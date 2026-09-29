"""Tests for bin/cliffhanger: settings.json edits must be safe, stats must read the hook's log."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import pytest
from conftest import CLI


@pytest.fixture
def cli(tmp_path):
    home = tmp_path / "home"

    def run(*args):
        env = {**os.environ, "CLIFFHANGER_HOME": str(home)}
        proc = subprocess.run([sys.executable, str(CLI), *args], capture_output=True, text=True, env=env, timeout=30)
        return proc

    run.home = home
    return run


def write_log(home, rows):
    home.mkdir(parents=True, exist_ok=True)
    with open(home / "log.jsonl", "w") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def row(rule, action, session="s1", observe=False, days_ago=0):
    ts = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat(timespec="seconds")
    return {"ts": ts, "session": session, "action": action, "rule": rule, "observe": observe}


def test_install_keeps_existing_hooks_and_backs_up(tmp_path, cli):
    settings = tmp_path / "settings.json"
    original = {"model": "opus", "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "say done"}]}],
                                           "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command",
                                                                                         "command": "guard"}]}]}}
    settings.write_text(json.dumps(original))
    proc = cli("install", "--settings", str(settings), "--json")
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    data = json.loads(settings.read_text())
    assert data["model"] == "opus"
    assert data["hooks"]["PreToolUse"] == original["hooks"]["PreToolUse"]
    assert data["hooks"]["Stop"][0] == original["hooks"]["Stop"][0]
    assert "cliffhanger.py" in data["hooks"]["Stop"][1]["hooks"][0]["command"]
    assert "cliffhanger.py" in data["hooks"]["SubagentStop"][0]["hooks"][0]["command"]
    assert json.loads(open(result["backup"]).read()) == original


def test_install_is_idempotent(tmp_path, cli):
    settings = tmp_path / "settings.json"
    cli("install", "--settings", str(settings))
    proc = cli("install", "--settings", str(settings))
    assert "Already installed" in proc.stdout
    data = json.loads(settings.read_text())
    assert len(data["hooks"]["Stop"]) == 1


def test_install_creates_missing_file(tmp_path, cli):
    settings = tmp_path / "new" / "settings.json"
    proc = cli("install", "--settings", str(settings), "--no-subagent")
    assert proc.returncode == 0
    data = json.loads(settings.read_text())
    assert list(data["hooks"]) == ["Stop"]


def test_install_refuses_invalid_json(tmp_path, cli):
    settings = tmp_path / "settings.json"
    settings.write_text('{"hooks": {,}')
    proc = cli("install", "--settings", str(settings))
    assert proc.returncode == 1
    assert "not valid JSON" in proc.stderr
    assert settings.read_text() == '{"hooks": {,}'


def test_install_refuses_wrong_shapes(tmp_path, cli):
    settings = tmp_path / "settings.json"
    settings.write_text('{"hooks": {"Stop": "nope"}}')
    proc = cli("install", "--settings", str(settings))
    assert proc.returncode == 1 and "is not a list" in proc.stderr
    settings.write_text("[1, 2]")
    proc = cli("install", "--settings", str(settings))
    assert proc.returncode == 1 and "JSON object" in proc.stderr


def test_install_dry_run_writes_nothing(tmp_path, cli):
    settings = tmp_path / "settings.json"
    settings.write_text("{}")
    proc = cli("install", "--settings", str(settings), "--dry-run")
    assert "Would add" in proc.stdout
    assert settings.read_text() == "{}"


def test_install_follows_symlink(tmp_path, cli):
    real = tmp_path / "dotfiles" / "settings.json"
    real.parent.mkdir()
    real.write_text("{}")
    link = tmp_path / "settings.json"
    link.symlink_to(real)
    cli("install", "--settings", str(link))
    assert link.is_symlink()
    assert "Stop" in json.loads(real.read_text())["hooks"]


def test_uninstall_removes_only_cliffhanger(tmp_path, cli):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "say done"}]}]}}))
    cli("install", "--settings", str(settings))
    proc = cli("uninstall", "--settings", str(settings))
    assert "Removed 2" in proc.stdout
    data = json.loads(settings.read_text())
    assert data == {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "say done"}]}]}}


def test_uninstall_drops_empty_hooks_object(tmp_path, cli):
    settings = tmp_path / "settings.json"
    settings.write_text('{"theme": "dark"}')
    cli("install", "--settings", str(settings))
    cli("uninstall", "--settings", str(settings))
    assert json.loads(settings.read_text()) == {"theme": "dark"}


def test_uninstall_when_absent(tmp_path, cli):
    settings = tmp_path / "settings.json"
    settings.write_text("{}")
    proc = cli("uninstall", "--settings", str(settings))
    assert proc.returncode == 0 and "No cliffhanger hook" in proc.stdout


def test_on_off(cli):
    proc = cli("off")
    assert "off" in proc.stdout and (cli.home / "off").exists()
    proc = cli("on", "--json")
    assert json.loads(proc.stdout) == {"state": "on"} and not (cli.home / "off").exists()


def test_status_json(tmp_path, cli):
    settings = tmp_path / "settings.json"
    cli("install", "--settings", str(settings))
    data = json.loads(cli("status", "--settings", str(settings), "--json").stdout)
    assert data["installed_in_settings"] == ["Stop", "SubagentStop"] and data["enabled"] is True


def test_stats_empty(cli):
    proc = cli("stats")
    assert proc.returncode == 0 and "No stops logged this week" in proc.stdout


def test_stats_counts_and_windows(cli):
    write_log(cli.home, [
        row("open-items", "block", "s1"), row("offers-to-continue", "block", "s2"),
        row("open-items", "block", "s1"), row("checklist-done", "allow", "s1"),
        row("blocker-token", "allow", "s3"), row("max-continuations", "allow", "s2"),
        row("offers-to-continue", "block", "s4", observe=True),
        row("open-items", "block", "old", days_ago=10),
    ])
    proc = cli("stats")
    assert "caught 3 early stops this week in 2 of 4 sessions" in proc.stdout
    assert "observe mode: would have caught 1" in proc.stdout
    assert "hit the continuation cap" in proc.stdout
    data = json.loads(cli("stats", "--days", "30", "--json").stdout)
    assert data["caught"] == 4 and data["caught_by_rule"]["open-items"] == 3


def test_stats_skips_corrupt_lines(cli):
    cli.home.mkdir(parents=True)
    (cli.home / "log.jsonl").write_text("garbage\n" + json.dumps(row("open-items", "block")) + "\n{}\n")
    assert "caught 1 early stop this week" in cli("stats").stdout


def test_stats_rejects_bad_days(cli):
    proc = cli("stats", "--days", "0")
    assert proc.returncode == 2


def test_help_for_every_command(cli):
    for command in ("stats", "on", "off", "status", "install", "uninstall"):
        proc = cli(command, "--help")
        assert proc.returncode == 0 and "usage: cliffhanger" in proc.stdout
    assert "CLIFFHANGER_OBSERVE" in cli("--help").stdout
    assert "0.1.0" in cli("--version").stdout


def test_uninstall_tolerates_odd_shapes_and_keeps_foreign_groups(tmp_path, cli):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"hooks": {"Stop": [{"hooks": []}], "SubagentStop": "weird"}}))
    assert "No cliffhanger hook" in cli("uninstall", "--settings", str(settings)).stdout
    data = {"hooks": {"Stop": [{"hooks": []}, {"matcher": "", "hooks": [{"type": "command", "command": "x"}]}]}}
    settings.write_text(json.dumps(data))
    cli("install", "--settings", str(settings), "--no-subagent")
    cli("uninstall", "--settings", str(settings))
    assert json.loads(settings.read_text()) == data
