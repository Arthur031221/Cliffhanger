# Changelog

## Unreleased

- Detect Traditional Chinese versions of the early-stop patterns when no checklist exists.
- Apply checklist-tool changes only after successful results. Failed or unresolved `TaskUpdate`
  and `TodoWrite` calls preserve the previous checklist, so unfinished steps remain visible.
- Document that checklist completion does not verify test runs or detect code changes after tests.

## 0.1.0 (2026-09-30)

- Stop and SubagentStop hook (`hooks/cliffhanger.py`, stdlib only, under 200 lines). Blocks the end
  of a turn while the agent's checklist has open items. Reads TaskCreate/TaskUpdate, TodoWrite, and
  Markdown `- [ ]` checklists. With no checklist, matches the four early-stop patterns from
  Anthropic's Opus 5.5 guide plus reports of unverified work.
- Allows `BLOCKED:` and `NEEDS-YOU:` lines, running background tasks, plan mode, and stops after
  `CLIFFHANGER_MAX` (default 3) continuations per user turn.
- Waits (bounded) for the final message to reach the transcript before reading the checklist.
- Observe mode (`CLIFFHANGER_OBSERVE=1`) logs decisions without blocking.
- `cliffhanger` CLI: `stats`, `on`, `off`, `status`, `install`, `uninstall`, with `--json`.
- `SKILL.md` for Claude Code and the Agent Skills format, `AGENTS.md` for agents without hooks.
- Plugin manifest and marketplace entry, `/cliffhanger:stats` command.
- Benchmark harness in `bench/`: 12 multi-part tasks, baseline and treatment arms, deterministic
  scoring.
