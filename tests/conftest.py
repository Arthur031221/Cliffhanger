"""Helpers that build synthetic Claude Code transcripts.

Record shapes copy real transcripts from Claude Code 2.1.284: TaskCreate results carry the
new id in toolUseResult.task.id, TaskUpdate carries taskId and status, TodoWrite carries the
whole list, and prompts carry turnOrigin.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / "hooks" / "cliffhanger.py"
CLI = ROOT / "bin" / "cliffhanger"


def load(name, path):
    loader = SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


hook = load("cliffhanger_hook", HOOK)
cli = load("cliffhanger_cli", CLI)


class Transcript:
    def __init__(self, path: Path):
        self.path = path
        self.records = []
        self._n = 0

    def _id(self):
        self._n += 1
        return f"toolu_{self._n:04d}"

    def prompt(self, text, origin="sdk"):
        self.records.append({"type": "user", "turnOrigin": origin, "promptSource": origin,
                             "message": {"role": "user", "content": text}})
        return self

    def say(self, text, sidechain=False):
        self.records.append({"type": "assistant", "isSidechain": sidechain,
                             "message": {"role": "assistant", "content": [{"type": "text", "text": text}]}})
        return self

    def tool(self, name, inp, result="ok", tool_use_result=None, is_error=False):
        tid = self._id()
        self.records.append({"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "tool_use", "id": tid, "name": name, "input": inp}]}})
        block = {"type": "tool_result", "tool_use_id": tid, "content": result}
        if is_error:
            block["is_error"] = True
        rec = {"type": "user", "message": {"role": "user", "content": [block]}}
        if tool_use_result is not None:
            rec["toolUseResult"] = tool_use_result
        self.records.append(rec)
        return self

    def task_create(self, subject, task_id, is_error=False):
        return self.tool("TaskCreate", {"subject": subject, "description": subject, "activeForm": subject},
                         result=f"Task #{task_id} created successfully: {subject}",
                         tool_use_result=None if is_error else {"task": {"id": str(task_id), "subject": subject}},
                         is_error=is_error)

    def task_update(self, task_id, status):
        return self.tool("TaskUpdate", {"taskId": str(task_id), "status": status},
                         result=f"Updated task #{task_id} status",
                         tool_use_result={"success": True, "taskId": str(task_id)})

    def todo(self, *items):
        todos = [{"content": c, "status": s, "activeForm": c} for c, s in items]
        return self.tool("TodoWrite", {"todos": todos}, result="Todos have been modified successfully")

    def write(self):
        with open(self.path, "w", encoding="utf-8") as fh:
            for rec in self.records:
                fh.write(json.dumps(rec) + "\n")
        return str(self.path)


@pytest.fixture
def transcript(tmp_path):
    return Transcript(tmp_path / "session.jsonl")


@pytest.fixture
def run_hook(tmp_path):
    home = tmp_path / "home"

    def run(payload, env=None, raw=None):
        full = {"hook_event_name": "Stop", "session_id": "s1", "stop_hook_active": False,
                "last_assistant_message": "", "cwd": str(tmp_path)}
        full.update(payload)
        environ = {**os.environ, "CLIFFHANGER_HOME": str(home), "CLIFFHANGER_SYNC_MS": "200"}
        for key in ("CLIFFHANGER_OBSERVE", "CLIFFHANGER_MAX", "CLIFFHANGER_DISABLE"):
            environ.pop(key, None)
        environ.update(env or {})
        proc = subprocess.run([sys.executable, str(HOOK)], input=raw if raw is not None else json.dumps(full),
                              capture_output=True, text=True, env=environ, timeout=30)
        out = json.loads(proc.stdout) if proc.stdout.strip() else None
        log = home / "log.jsonl"
        entries = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
        return proc, out, entries

    run.home = home
    return run
