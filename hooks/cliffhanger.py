#!/usr/bin/env python3
"""Stop and SubagentStop hook: block the end of a turn while the agent's checklist has open items,
or, with no checklist, while its last message is one of the four early stops. Stdlib only. Fails open."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HOME = Path(os.environ.get("CLIFFHANGER_HOME") or Path.home() / ".cliffhanger")
TOKEN = re.compile(r"\b(?:BLOCKED|NEEDS-YOU):")
BOX = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+\[([ xX])\]\s+(.+?)\s*$", re.M)
F = re.I | re.M

PATTERNS = [  # (rule, description, regex): the four early stops in Anthropic's Opus 5.5 guide, plus one
    ("announces-next-step", "a summary that announces the next step instead of taking it", re.compile(
        r"\bnext steps?\s*(?:is|are|would be|will be|:)|\bnext,? I(?:'ll| will| would| plan to)\b"
        r"|\b(?:then|after that),? I(?:'ll| will)\b|\bwhat(?:'s| is) left\b|\bI(?:'ll| will) (?:now |next |then )?"
        r"(?:continue|proceed|move on|start on|tackle|work on|run|add|write|finish)\b"
        r"|^\W*(?:remaining|still to do|left to do|todo|next steps?)(?: work| items| steps)?\W*$", F)),
    ("offers-to-continue", "an offer to carry on that waits for an answer nobody will give", re.compile(
        r"\b(?:do you )?want me to\b|\bwould you like me to\b|\bshall I\b|\bsay the word\b"
        r"|\bshould I (?:continue|proceed|go ahead|keep going)\b|\bonce you (?:approve|confirm|reply)\b"
        r"|\blet me know (?:if|whether|when) (?:you(?:'d| would)? (?:like|want) me to|I should|to (?:continue|proceed))"
        r"|\bif you(?:'d| would)? (?:like|want|prefer),? I (?:can|could|will|'ll)\b|\bhappy to (?:continue|proceed)\b"
        r"|\bI can (?:continue|proceed|keep going|finish|go ahead)\b[^.?!\n]*\bif\b", F)),
    ("decisions-for-user", "a list of decisions, none of which blocks the rest of the work", re.compile(
        r"\bdecisions? (?:for you|you(?:'ll)? need to make|needed from you)\b|\bbefore I (?:continue|proceed)\b"
        r"|\b(?:a few|some|two|three|several|couple of) (?:open )?(?:decisions|questions|choices)\b"
        r"|^\W*options?\W*:?\W*$|\bwhich (?:option|approach) (?:do you|would you|should I)\b"
        r"|\bhow would you like (?:me )?to (?:proceed|handle)\b", F)),
    ("good-place-to-report", "a stop to report because a milestone felt like a good place", re.compile(
        r"\bgood (?:stopping|breaking|pausing) (?:point|place)\b|\bnatural (?:stopping|pause|break)"
        r"|\b(?:good|natural|logical) (?:place|point|time) to (?:stop|pause|check in|report)\b"
        r"|\bI'll (?:pause|stop) (?:here|now|for now)\b|\bcheck(?:ing)? in (?:with you|before)\b"
        r"|\bin (?:the |a )?(?:next|follow-up) (?:turn|session|message)\b", F)),
    ("leaves-work-unverified", "a report that the work was never run or tested", re.compile(  # ours, not the guide's
        r"\b(?:haven't|have not|couldn't|could not|didn't|did not) (?:yet )?(?:been able to )?(?:run|execute) "
        r"(?:the |any )?(?:tests?|pytest|test suite|suite)\b|\bunverified\b|\buntested\b|\bnot (?:yet )?tested\b", F)),
]
BLOCKERS = re.compile(
    r"\bneeds? (?:your|you to)\b|\b(?:cannot|can't|unable to) (?:proceed|continue)\b"
    r"|\bcredentials?\b|\bapi[ _-]?key\b|\baccess token\b|\bpermission (?:denied|to)\b|\bcan(?:not|'t) be undone\b"
    r"|\bwhich one of these\b|\b(?:destructive|irreversible)\b|\bprotected (?:branch|environment)\b"
    r"|\b(?:requires?|needs?) (?:your )?(?:approval|confirmation|sign-?off)\b", F)
KEYS = ("TaskCreate", "TaskUpdate", "TodoWrite", "Task #", "turnOrigin", "[ ]", "[x]", "[X]")


def read_transcript(path, last_msg, wait_ms):
    """Parse the records the checklist needs, after waiting (bounded) for the final message to hit disk."""
    if not path or not os.path.exists(path):
        return []
    tail = json.dumps(last_msg.strip()[-40:], ensure_ascii=False)[1:-1]
    deadline = time.monotonic() + wait_ms / 1000
    while True:
        with open(path, encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
        if tail in raw[-400_000:] or time.monotonic() >= deadline:
            break
        time.sleep(0.1)
    spans = set()  # jump to lines that mention a key: str.find beats splitting a 10+ MB transcript
    for key in KEYS:
        i = raw.find(key)
        while i != -1:
            end = raw.find("\n", i) % (len(raw) + 1)  # no newline: -1 wraps to len(raw)
            spans.add((raw.rfind("\n", 0, i) + 1, end))
            i = raw.find(key, end)
    records = [json.loads(raw[a:b]) for a, b in sorted(spans) if raw[a:b].rstrip().endswith("}")]
    return [r for r in records if isinstance(r, dict) and not r.get("isSidechain")]


def markdown_items(text):
    return [(m.group(2), "completed" if m.group(1) in "xX" else "pending") for m in BOX.finditer(text or "")]


def checklist(records, last_msg=""):
    """Rebuild the checklist from TaskCreate/TaskUpdate, TodoWrite, or `- [ ]` lines written this turn."""
    tasks, creates, todo, md, source = {}, {}, None, None, None
    for rec in records:
        if rec.get("type") == "user" and rec.get("turnOrigin") in ("human", "sdk", "scheduled"):
            md = None  # a new prompt, not a background-task notification: old markdown lists expire
        content = (rec.get("message") or {}).get("content")
        for b in content if isinstance(content, list) else []:
            kind, name, inp = b.get("type"), b.get("name"), b.get("input") or {}
            if kind == "tool_use" and name == "TodoWrite":
                todo, source = [(t.get("content", ""), t.get("status", "")) for t in inp.get("todos", [])], "todo"
            elif kind == "tool_use" and name == "TaskCreate":
                creates[b.get("id")] = inp.get("subject") or inp.get("description") or "task"
            elif kind == "tool_use" and name == "TaskUpdate":
                tid = str(inp.get("taskId"))
                entry = tasks.setdefault(tid, ["task " + tid, "pending"])
                entry[0], entry[1], source = inp.get("subject") or entry[0], inp.get("status") or entry[1], "tasks"
            elif kind == "tool_result" and b.get("tool_use_id") in creates:
                subject, found = creates.pop(b["tool_use_id"]), re.search(r"Task #(\w+)", json.dumps(b.get("content")))
                tid = ((rec.get("toolUseResult") or {}).get("task") or {}).get("id") or (found and found.group(1))
                if not b.get("is_error"):
                    tasks.setdefault(str(tid or len(tasks) + 1), [subject, "pending"])
                    source = "tasks"
            elif kind == "text" and rec.get("type") == "assistant" and markdown_items(b.get("text")):
                md = markdown_items(b.get("text"))
    md = markdown_items(last_msg) or md
    source = source or ("markdown" if md else None)
    return source, {"tasks": [tuple(v) for v in tasks.values()], "todo": todo, "markdown": md, None: []}[source]


def decide(payload, items, source, count, max_count):
    """Pure decision function. Returns (action, rule, open_items, matched_text)."""
    msg = payload.get("last_assistant_message") or ""
    open_items = [t for t, s in items if s not in ("completed", "deleted")]
    ordered = [("allow", "blocker-token", TOKEN.search(msg)),
               ("allow", "background-work", payload.get("background_tasks")),
               ("allow", "plan-mode", payload.get("permission_mode") == "plan"),
               ("allow", "max-continuations", count >= max_count), ("block", "open-items", open_items),
               ("allow", "checklist-done", source), ("allow", "blocker-phrase", BLOCKERS.search(msg))]
    for action, rule, hit in ordered:  # background work wakes the session itself. A checklist beats regexes
        if hit:
            return action, rule, open_items, None
    for rule, _, rx in PATTERNS:
        m = rx.search(msg)
        if m:
            return "block", rule, [], m.group(0).strip()
    return "allow", "no-pattern", [], None


def reason(rule, open_items, matched):
    if rule == "open-items":
        shown = "; ".join(t[:80] for t in open_items[:5])
        more = f"; and {len(open_items) - 5} more" if len(open_items) > 5 else ""
        return (f"Open items: {shown}{more}. Continue with them. If one is blocked, say what is "
                "blocking it on a line that starts with BLOCKED:.")
    what = next(d for r, d, _ in PATTERNS if r == rule)
    return (f'Your last message ended the turn with {what} ("{matched}"). If work the user asked for '
            "is still owed, do it now instead of describing or offering it. If everything asked for is "
            "done, end with the final report and no offer. If something only the user can clear is in "
            "the way, write BLOCKED: <what> <what you need> on its own line.")


def first_copy(state_dir, digest):  # the plugin and a settings.json install can both fire: first copy decides
    lock, now = state_dir / f"{digest}.lock", time.time()
    try:
        os.close(os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
    except FileExistsError:
        if now - lock.stat().st_mtime < 30:
            return False
        lock.touch()
    for old in (p for p in state_dir.glob("*.lock") if now - p.stat().st_mtime > 3600):
        old.unlink()
    return True


def main():
    payload = json.loads(sys.stdin.read() or "{}")
    event = payload.get("hook_event_name", "Stop")
    internal = event == "SubagentStop" and not payload.get("agent_type")  # prompt suggestions, /btw
    if internal or os.environ.get("CLIFFHANGER_DISABLE") == "1" or (HOME / "off").exists():
        return
    observe = os.environ.get("CLIFFHANGER_OBSERVE") == "1"
    msg = payload.get("last_assistant_message") or ""
    key = re.sub(r"[^A-Za-z0-9_-]", "_", "-".join(filter(None, [payload.get("session_id"), payload.get("agent_id")])))
    state_dir = HOME / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file = state_dir / f"{key or 'none'}.json"
    active = payload.get("stop_hook_active") and state_file.exists()  # false on a fresh user turn
    count = json.loads(state_file.read_text()).get("count", 0) if active else 0
    if not first_copy(state_dir, hashlib.sha1(f"{key}|{count}|{msg}".encode()).hexdigest()[:16]):
        return
    path = payload.get("agent_transcript_path") if event == "SubagentStop" else payload.get("transcript_path")
    source, items = checklist(read_transcript(path, msg, int(os.environ.get("CLIFFHANGER_SYNC_MS", "1500"))), msg)
    max_count = int(os.environ.get("CLIFFHANGER_MAX", "3"))
    action, rule, open_items, matched = decide(payload, items, source, count, max_count)
    block = action == "block" and not observe
    state_file.write_text(json.dumps({"count": count + 1 if block else count}))
    entry = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "session": payload.get("session_id"),
             "event": event, "agent": payload.get("agent_type"), "action": action, "observe": observe,
             "rule": rule, "open": open_items[:10], "match": matched, "source": source,
             "continuation": count, "cwd": payload.get("cwd")}
    with open(HOME / "log.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    if block:
        print(json.dumps({"decision": "block", "reason": reason(rule, open_items, matched)}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # fail open: a broken hook must never trap the session
        HOME.mkdir(parents=True, exist_ok=True)
        with open(HOME / "errors.log", "a", encoding="utf-8") as fh:
            fh.write(f"{datetime.now(timezone.utc).isoformat()} {type(exc).__name__}: {exc}\n")
    sys.exit(0)
