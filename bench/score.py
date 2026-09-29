#!/usr/bin/env python3
"""Deterministic scoring for the cliffhanger benchmark.

score.py check <repo_dir> <task_id>     print the check results for one run as JSON
score.py summarize <out_dir>            write the results table (Markdown) for a finished run
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parent
TASKS = {t["id"]: t for t in json.loads((BENCH / "tasks.json").read_text())}
PYTHON = BENCH.parent / ".venv" / "bin" / "python"


def read(repo, rel):
    path = repo / rel
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def unreleased(repo):
    text = read(repo, "CHANGELOG.md")
    match = re.search(r"^## Unreleased\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    return match.group(1) if match else ""


def run_pytest(repo):
    python = str(PYTHON) if PYTHON.exists() else sys.executable
    proc = subprocess.run([python, "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=repo,
                          capture_output=True, text=True, timeout=120)
    passed = re.search(r"(\d+) passed", proc.stdout)
    return proc.returncode == 0, int(passed.group(1)) if passed else 0


def check(repo: Path, task_id: str):
    results = []
    tests = "\n".join(p.read_text(errors="replace") for p in sorted((repo / "tests").glob("*.py")))
    for c in TASKS[task_id]["checks"]:
        kind, flags = c["kind"], re.I | re.M
        if kind == "contains":
            ok = bool(re.search(c["pattern"], read(repo, c["file"]), flags))
            label = f"{c['file']} contains /{c['pattern']}/"
        elif kind == "absent":
            ok = not re.search(c["pattern"], read(repo, c["file"]), flags)
            label = f"{c['file']} lacks /{c['pattern']}/"
        elif kind == "tests_contain":
            ok = bool(re.search(c["pattern"], tests, flags))
            label = f"tests mention /{c['pattern']}/"
        elif kind == "changelog":
            ok = bool(re.search(c["pattern"], unreleased(repo), flags))
            label = f"CHANGELOG Unreleased mentions /{c['pattern']}/"
        elif kind == "pytest":
            green, count = run_pytest(repo)
            ok = green and count >= c["min_tests"]
            label = f"pytest green with >= {c['min_tests']} tests (got {count}, green={green})"
        else:
            raise ValueError(kind)
        results.append({"check": label, "ok": ok})
    return {"task": task_id, "done": all(r["ok"] for r in results),
            "passed": sum(r["ok"] for r in results), "total": len(results), "checks": results}


def transcript_tokens(session_id):
    """Sum usage over the session transcript, one count per API message id."""
    if not session_id:
        return None
    paths = list((Path.home() / ".claude" / "projects").glob(f"*/{session_id}.jsonl"))
    if not paths:
        return None
    seen, totals = set(), {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}
    for line in paths[0].read_text(errors="replace").splitlines():
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        msg = rec.get("message") if isinstance(rec, dict) else None
        if rec.get("type") != "assistant" or not isinstance(msg, dict) or msg.get("id") in seen:
            continue
        seen.add(msg.get("id"))
        usage = msg.get("usage") or {}
        totals["input"] += usage.get("input_tokens", 0)
        totals["output"] += usage.get("output_tokens", 0)
        totals["cache_read"] += usage.get("cache_read_input_tokens", 0)
        totals["cache_write"] += usage.get("cache_creation_input_tokens", 0)
    return totals


def load_run(run_dir: Path):
    invs = []
    for path in sorted(run_dir.glob("inv*.json"), key=lambda p: int(re.sub(r"\D", "", p.stem) or 0)):
        try:
            invs.append(json.loads(path.read_text()))
        except ValueError:
            invs.append({"is_error": True, "result": f"unparseable output in {path.name}"})
    scores = []
    for path in sorted(run_dir.glob("score*.json"), key=lambda p: int(re.sub(r"\D", "", p.stem) or 0)):
        scores.append(json.loads(path.read_text()))
    log = run_dir / "home" / "log.jsonl"
    hook = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
    return invs, scores, hook


def summarize(out: Path):
    rows, agg = [], {}
    for arm in ("baseline", "treatment"):
        agg[arm] = {"tasks": 0, "done_first": 0, "done_final": 0, "owed_at_first_stop": 0, "nudges": 0,
                    "cost": 0.0, "output_tokens": 0, "turns": 0, "hook_block": 0, "errors": 0}
        for task_id in TASKS:
            run_dir = out / arm / task_id
            if not run_dir.exists():
                continue
            invs, scores, hook = load_run(run_dir)
            if not invs:
                continue
            a = agg[arm]
            a["tasks"] += 1
            first_done = bool(scores and scores[0]["done"])
            final_done = bool(scores and scores[-1]["done"])
            sid = next((i.get("session_id") for i in invs if i.get("session_id")), None)
            tokens = transcript_tokens(sid) or {}
            cost = invs[-1].get("total_cost_usd") or 0.0  # cumulative across --resume
            blocks = sum(1 for h in hook if h["action"] == "block")
            a["done_first"] += first_done
            a["done_final"] += final_done
            a["owed_at_first_stop"] += not first_done
            a["nudges"] += len(invs) - 1
            a["cost"] += cost
            a["output_tokens"] += tokens.get("output", 0)
            a["turns"] += sum(i.get("num_turns") or 0 for i in invs)
            a["hook_block"] += blocks
            a["errors"] += sum(1 for i in invs if i.get("is_error"))
            first_hook = [h for h in hook if h.get("session") == sid]
            rows.append({
                "arm": arm, "task": task_id, "session": sid,
                "first": f"{scores[0]['passed']}/{scores[0]['total']}" if scores else "n/a",
                "final": f"{scores[-1]['passed']}/{scores[-1]['total']}" if scores else "n/a",
                "nudges": len(invs) - 1, "turns": sum(i.get("num_turns") or 0 for i in invs),
                "cost": round(cost, 4), "out_tokens": tokens.get("output", 0), "hook": ", ".join(
                    f"{h['action']}:{h['rule']}" for h in first_hook) or "none",
                "errors": [i.get("result", "")[:160] for i in invs if i.get("is_error")],
                "first_result": (invs[0].get("result") or "")[-300:].replace("\n", " "),
            })
    (out / "summary.json").write_text(json.dumps({"aggregate": agg, "rows": rows}, indent=2))
    lines = ["| arm | task | checks after 1st stop | final | nudges | turns | cost USD | output tokens | hook decisions |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['arm']} | {r['task']} | {r['first']} | {r['final']} | {r['nudges']} | {r['turns']} | "
                     f"{r['cost']:.4f} | {r['out_tokens']} | {r['hook']} |")
    lines += ["", "| arm | tasks run | done at first stop | work owed at first stop | done after nudges | "
                  "nudges | hook blocks | total cost USD | output tokens | errors |", "|---|---|---|---|---|---|---|---|---|---|"]
    for arm, a in agg.items():
        lines.append(f"| {arm} | {a['tasks']} | {a['done_first']} | {a['owed_at_first_stop']} | {a['done_final']} | "
                     f"{a['nudges']} | {a['hook_block']} | {a['cost']:.2f} | {a['output_tokens']} | {a['errors']} |")
    (out / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "check":
        print(json.dumps(check(Path(sys.argv[2]), sys.argv[3]), indent=2))
    elif len(sys.argv) == 3 and sys.argv[1] == "summarize":
        summarize(Path(sys.argv[2]))
    else:
        print(__doc__)
        sys.exit(2)
