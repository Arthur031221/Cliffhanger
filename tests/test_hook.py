"""End-to-end tests of hooks/cliffhanger.py: one test per rule, allow and block paths."""
from __future__ import annotations

import json
import threading
import time

import pytest
from conftest import hook


def test_open_task_items_block(transcript, run_hook):
    t = transcript.prompt("add endpoint, test, docs")
    t.task_create("Add /health endpoint", 1).task_create("Test /health", 2).task_create("Document /health", 3)
    t.task_update(1, "completed").say("Endpoint is in. Next I'll write the test.")
    proc, out, log = run_hook({"transcript_path": t.write(),
                               "last_assistant_message": "Endpoint is in. Next I'll write the test."})
    assert proc.returncode == 0
    assert out["decision"] == "block"
    assert out["reason"].startswith("Open items: Test /health; Document /health. Continue with them.")
    assert "BLOCKED:" in out["reason"]
    assert log[-1]["rule"] == "open-items" and log[-1]["source"] == "tasks"


def test_all_tasks_done_allows_even_with_offer(transcript, run_hook):
    t = transcript.prompt("two things")
    t.task_create("A", 1).task_create("B", 2).task_update(1, "completed").task_update(2, "completed")
    msg = "Both done, tests pass. Want me to also add a CI workflow?"
    proc, out, log = run_hook({"transcript_path": t.write(), "last_assistant_message": msg})
    assert out is None
    assert log[-1]["action"] == "allow" and log[-1]["rule"] == "checklist-done"


def test_deleted_task_is_not_open(transcript, run_hook):
    t = transcript.task_create("A", 1).task_create("Obsolete", 2).task_update(1, "completed")
    t.task_update(2, "deleted")
    _, out, log = run_hook({"transcript_path": t.write(), "last_assistant_message": "Done."})
    assert out is None and log[-1]["rule"] == "checklist-done"


def test_failed_task_create_is_ignored(transcript, run_hook):
    t = transcript.task_create("A", 1).task_create("never created", 2, is_error=True).task_update(1, "completed")
    _, out, log = run_hook({"transcript_path": t.write(), "last_assistant_message": "Done."})
    assert out is None and log[-1]["rule"] == "checklist-done"


def test_todowrite_open_items_block(transcript, run_hook):
    t = transcript.todo(("Add model field", "completed"), ("Migrate data", "in_progress"), ("Update docs", "pending"))
    _, out, log = run_hook({"transcript_path": t.write(), "last_assistant_message": "Field added."})
    assert out["decision"] == "block"
    assert "Migrate data; Update docs" in out["reason"]
    assert log[-1]["source"] == "todo"


def test_latest_todowrite_wins(transcript, run_hook):
    t = transcript.todo(("A", "pending"), ("B", "pending")).todo(("A", "completed"), ("B", "completed"))
    _, out, log = run_hook({"transcript_path": t.write(), "last_assistant_message": "All done."})
    assert out is None and log[-1]["rule"] == "checklist-done"


def test_markdown_checklist_in_last_message_blocks(transcript, run_hook):
    msg = "Progress:\n- [x] endpoint\n- [ ] tests\n- [ ] changelog line"
    _, out, log = run_hook({"transcript_path": transcript.prompt("go").write(), "last_assistant_message": msg})
    assert out["decision"] == "block"
    assert "Open items: tests; changelog line." in out["reason"]
    assert log[-1]["source"] == "markdown"


def test_markdown_checklist_from_earlier_prompt_expires(transcript, run_hook):
    t = transcript.prompt("first task").say("Plan:\n- [ ] one\n- [ ] two").prompt("unrelated question")
    t.say("The answer is 42.")
    _, out, log = run_hook({"transcript_path": t.write(), "last_assistant_message": "The answer is 42."})
    assert out is None and log[-1]["rule"] == "no-pattern"


def test_background_notification_does_not_expire_markdown(transcript, run_hook):
    t = transcript.prompt("go").say("Plan:\n- [x] one\n- [ ] two")
    t.prompt("<task-notification>", origin="task_notification").say("Build finished.")
    _, out, _ = run_hook({"transcript_path": t.write(), "last_assistant_message": "Build finished."})
    assert out["decision"] == "block" and "two" in out["reason"]


def test_sidechain_records_are_ignored(transcript, run_hook):
    t = transcript.prompt("go").say("- [ ] subagent private item", sidechain=True).say("Done.")
    _, out, log = run_hook({"transcript_path": t.write(), "last_assistant_message": "Done."})
    assert out is None and log[-1]["source"] is None


def test_blocked_token_allows_with_open_items(transcript, run_hook):
    t = transcript.task_create("Deploy to staging", 1)
    msg = "Code is merged.\nBLOCKED: staging deploy. Need STAGING_TOKEN, it is not set in this environment."
    _, out, log = run_hook({"transcript_path": t.write(), "last_assistant_message": msg})
    assert out is None
    assert log[-1]["rule"] == "blocker-token" and log[-1]["open"] == ["Deploy to staging"]


def test_needs_you_token_allows(run_hook):
    _, out, log = run_hook({"last_assistant_message": "NEEDS-YOU: pick the license, MIT or Apache-2.0."})
    assert out is None and log[-1]["rule"] == "blocker-token"


def test_lowercase_blocked_is_not_the_token(run_hook):
    _, out, _ = run_hook({"last_assistant_message": "The request was blocked: want me to retry it?"})
    assert out["decision"] == "block"


def test_background_work_allows(transcript, run_hook):
    t = transcript.task_create("Wait for build", 1)
    payload = {"transcript_path": t.write(), "last_assistant_message": "Build started in the background.",
               "background_tasks": [{"id": "b1", "type": "shell", "status": "running", "command": "make"}]}
    _, out, log = run_hook(payload)
    assert out is None and log[-1]["rule"] == "background-work"


def test_plan_mode_allows(run_hook):
    _, out, log = run_hook({"permission_mode": "plan", "last_assistant_message": "Here is the plan. Shall I start?"})
    assert out is None and log[-1]["rule"] == "plan-mode"


def test_announces_next_step_blocks(run_hook):
    msg = "I refactored the store and all 14 tests pass. The next step is updating the API handlers."
    _, out, log = run_hook({"last_assistant_message": msg})
    assert out["decision"] == "block"
    assert log[-1]["rule"] == "announces-next-step" and log[-1]["match"].lower().startswith("next step")


def test_offers_to_continue_blocks(run_hook):
    _, out, log = run_hook({"last_assistant_message": "Migration 1 of 3 is done. Would you like me to continue?"})
    assert out["decision"] == "block" and log[-1]["rule"] == "offers-to-continue"
    assert '("Would you like me to")' in out["reason"]


def test_decision_list_blocks(run_hook):
    msg = "The parser is ported. A few decisions for you:\n1. Keep the old flag?\n2. Rename the module?"
    _, out, log = run_hook({"last_assistant_message": msg})
    assert out["decision"] == "block" and log[-1]["rule"] == "decisions-for-user"


def test_good_place_to_report_blocks(run_hook):
    msg = "Phase one is complete, which seems like a good stopping point. Here is what changed."
    _, out, log = run_hook({"last_assistant_message": msg})
    assert out["decision"] == "block" and log[-1]["rule"] == "good-place-to-report"


def test_traditional_chinese_real_transcript_offer_blocks(run_hook):
    # Captured from a real Traditional Chinese assistant transcript.
    msg = "要我接著加 ROI 輪廓、切換受試者、或包成可分享連結,跟我說一聲就好。"
    _, out, log = run_hook({"last_assistant_message": msg})
    assert out["decision"] == "block" and log[-1]["rule"] == "offers-to-continue"


@pytest.mark.parametrize(("msg", "rule"), [
    ("下一步是更新文件。", "announces-next-step"),
    ("要我繼續嗎？", "offers-to-continue"),
    ("有幾個選擇要你決定。", "decisions-for-user"),
    ("這是個適合停下的地方。", "good-place-to-report"),
    ("還沒跑過測試。", "leaves-work-unverified"),
])
def test_traditional_chinese_patterns_block(run_hook, msg, rule):
    _, out, log = run_hook({"last_assistant_message": msg})
    assert out["decision"] == "block" and log[-1]["rule"] == rule


def test_blocker_phrase_suppresses_pattern(run_hook):
    msg = "I cannot proceed without the database credentials. Want me to use SQLite in the meantime?"
    _, out, log = run_hook({"last_assistant_message": msg})
    assert out is None and log[-1]["rule"] == "blocker-phrase"


def test_blocker_phrase_does_not_override_open_items(transcript, run_hook):
    t = transcript.task_create("Write migration", 1)
    msg = "I need your approval before touching the schema."
    _, out, log = run_hook({"transcript_path": t.write(), "last_assistant_message": msg})
    assert out["decision"] == "block" and log[-1]["rule"] == "open-items"


def test_plain_final_report_allows(run_hook):
    msg = "Added GET /health, a test for it, a docs entry, and a changelog line. 15 tests pass."
    _, out, log = run_hook({"last_assistant_message": msg})
    assert out is None and log[-1]["rule"] == "no-pattern"


def test_counter_caps_continuations(run_hook):
    msg = "Step one done. Want me to keep going?"
    _, out, log = run_hook({"last_assistant_message": msg})
    assert out and log[-1]["continuation"] == 0
    for expected in (1, 2):
        _, out, log = run_hook({"last_assistant_message": msg + f" ({expected})", "stop_hook_active": True})
        assert out and log[-1]["continuation"] == expected
    _, out, log = run_hook({"last_assistant_message": msg + " (3)", "stop_hook_active": True})
    assert out is None and log[-1]["rule"] == "max-continuations"


def test_counter_resets_on_new_user_turn(run_hook):
    msg = "Want me to keep going?"
    run_hook({"last_assistant_message": msg})
    run_hook({"last_assistant_message": msg + " again", "stop_hook_active": True})
    _, out, log = run_hook({"last_assistant_message": msg + " fresh", "stop_hook_active": False})
    assert out and log[-1]["continuation"] == 0


def test_custom_max(run_hook):
    _, out, log = run_hook({"last_assistant_message": "Shall I continue?"}, env={"CLIFFHANGER_MAX": "0"})
    assert out is None and log[-1]["rule"] == "max-continuations"


def test_observe_mode_logs_but_never_blocks(run_hook):
    _, out, log = run_hook({"last_assistant_message": "Do you want me to continue?"}, env={"CLIFFHANGER_OBSERVE": "1"})
    assert out is None
    assert log[-1]["action"] == "block" and log[-1]["observe"] is True
    state = json.loads((run_hook.home / "state" / "s1.json").read_text())
    assert state["count"] == 0


def test_off_flag_and_disable_env(run_hook):
    run_hook.home.mkdir(parents=True)
    (run_hook.home / "off").write_text("")
    proc, out, log = run_hook({"last_assistant_message": "Want me to continue?"})
    assert proc.returncode == 0 and out is None and log == []
    (run_hook.home / "off").unlink()
    _, out, log = run_hook({"last_assistant_message": "Want me to continue?"}, env={"CLIFFHANGER_DISABLE": "1"})
    assert out is None and log == []


def test_subagent_stop_reads_agent_transcript(tmp_path, transcript, run_hook):
    t = transcript.todo(("Scan src/", "completed"), ("Scan tests/", "pending"))
    payload = {"hook_event_name": "SubagentStop", "agent_id": "a1", "agent_type": "Explore",
               "transcript_path": str(tmp_path / "main.jsonl"), "agent_transcript_path": t.write(),
               "last_assistant_message": "src/ scanned."}
    _, out, log = run_hook(payload)
    assert out["decision"] == "block" and "Scan tests/" in out["reason"]
    assert log[-1]["agent"] == "Explore"
    assert (run_hook.home / "state" / "s1-a1.json").exists()


def test_internal_subagent_is_skipped(run_hook):
    payload = {"hook_event_name": "SubagentStop", "agent_id": "a2", "agent_type": "",
               "last_assistant_message": "Want me to continue?"}
    _, out, log = run_hook(payload)
    assert out is None and log == []


def test_duplicate_copy_stays_silent(run_hook):
    payload = {"last_assistant_message": "Should I continue?"}
    _, first, _ = run_hook(payload)
    _, second, log = run_hook(payload)
    assert first["decision"] == "block"
    assert second is None and len(log) == 1


def test_waits_for_transcript_flush(transcript, run_hook):
    t = transcript.task_create("A", 1).task_create("B", 2)
    path = t.write()
    final = "All set, both items are complete."

    def late_flush():
        time.sleep(0.4)
        t.task_update(1, "completed").task_update(2, "completed").say(final).write()

    thread = threading.Thread(target=late_flush)
    thread.start()
    _, out, log = run_hook({"transcript_path": path, "last_assistant_message": final},
                           env={"CLIFFHANGER_SYNC_MS": "3000"})
    thread.join()
    assert out is None and log[-1]["rule"] == "checklist-done"


def test_missing_transcript_falls_back_to_patterns(tmp_path, run_hook):
    _, out, log = run_hook({"transcript_path": str(tmp_path / "nope.jsonl"),
                            "last_assistant_message": "Let me know if you'd like me to continue."})
    assert out["decision"] == "block" and log[-1]["source"] is None


def test_garbage_input_fails_open(run_hook):
    proc, out, log = run_hook({}, raw="this is not json")
    assert proc.returncode == 0 and out is None and log == []
    assert "JSONDecodeError" in (run_hook.home / "errors.log").read_text()


def test_empty_stdin_is_harmless(run_hook):
    proc, out, log = run_hook({}, raw="")
    assert proc.returncode == 0 and out is None
    assert log[-1]["rule"] == "no-pattern"


def test_reason_truncates_long_lists():
    items = [f"item {i}" for i in range(8)]
    text = hook.reason("open-items", items, None)
    assert "item 4; and 3 more." in text and "item 5" not in text


def test_markdown_items_parser():
    text = "1. [x] done thing\n2) [ ] open thing\n* [X] also done\nnot a [ ] box"
    assert hook.markdown_items(text) == [("done thing", "completed"), ("open thing", "pending"),
                                         ("also done", "completed")]


def test_task_ids_fall_back_to_result_text():
    records = [
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t1", "name": "TaskCreate",
                                                       "input": {"subject": "X"}}]}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1",
                                                  "content": "Task #7 created successfully: X"}]}},
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t2", "name": "TaskUpdate",
                                                       "input": {"taskId": "7", "status": "completed"}}]}},
    ]
    assert hook.checklist(records) == ("tasks", [("X", "completed")])


def test_waiting_on_approval_it_could_route_around_blocks(run_hook):
    # Observed in a real Sonnet 5.5 headless run: `python -m pytest` was denied, `pytest` was allowed.
    msg = ("Both parts are written, but I haven't been able to run pytest yet. The Bash tool is asking for "
           "approval on the pytest command, so nothing has been tested. Once you approve it, I'll run "
           "`python -m pytest -q`.")
    _, out, log = run_hook({"last_assistant_message": msg})
    assert out["decision"] == "block" and log[-1]["rule"] == "announces-next-step"
    assert "BLOCKED:" in out["reason"]


def test_unverified_work_blocks(run_hook):
    # Observed in two real Sonnet 5.5 headless runs: `python -m pytest` denied, `pytest` allowed but never tried.
    msg = ("I made all the code changes, but I couldn't run pytest. The sandbox blocked every attempt to run it "
           "and asked for approval, which isn't possible in this non-interactive session. So the tests are unverified.")
    _, out, log = run_hook({"last_assistant_message": msg})
    assert out["decision"] == "block" and log[-1]["rule"] == "leaves-work-unverified"


def test_untested_part_with_real_blocker_allows(run_hook):
    msg = "All 31 tests pass. The deploy script is untested because it needs AWS credentials I don't have."
    _, out, log = run_hook({"last_assistant_message": msg})
    assert out is None and log[-1]["rule"] == "blocker-phrase"
