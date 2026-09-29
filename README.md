# cliffhanger

A Stop hook and skill for Claude Code that keeps the agent working until every part of the task is
done or a real blocker is named, and counts every early stop it catches.

Sonnet 5.5 ended the turn without running the tests it was asked to run in 6 of 12 multi-step
tasks. With cliffhanger: 0 of 12, at 4 percent more cost.[^bench] In observe mode the hook flagged
exactly those 6 stops, and none of the other 42 final messages from the benchmark.[^detector]

Every one of those early stops followed a refused command: the allowlist said `pytest *`, the agent
reached for `python -m pytest`, got refused, and wrapped up. With every test command allowed,
neither arm stopped early and cliffhanger only added 13 percent to the bill. So this is not a fix
for a model that quits at random. It is a guard for the stops that do happen in unattended runs,
and a counter that tells you how often they happen to you.

[![ci](https://github.com/Arthur031221/cliffhanger/actions/workflows/ci.yml/badge.svg)](https://github.com/Arthur031221/cliffhanger/actions/workflows/ci.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![version 0.1.0](https://img.shields.io/badge/version-0.1.0-informational.svg)](CHANGELOG.md)

![The hook blocking an offer to continue, allowing a BLOCKED: line, then cliffhanger stats](demo/demo.gif)

[^bench]: 12 tasks with 4 to 6 parts each (code, tests, docs, changelog, "run pytest and make sure
    the whole suite passes") on a small WSGI app. `claude -p` with Claude Code 2.1.284,
    `claude-sonnet-5-5`, `--allowedTools "Read,Edit,Write,Bash(pytest *)"`, n=1 per task and arm,
    2026-09-30, MacBook Air M5. Baseline: the same hook in observe mode, no skill. Treatment: blocking
    hook plus `SKILL.md` through `--append-system-prompt-file`. The skill's advice for a refused
    command was written after we saw this failure in earlier runs, so this is not a held-out test.
    Raw tables, command lines, and the run we threw away: [bench/results.md](bench/results.md).
[^detector]: The regex bank alone, on the first final message of all 48 benchmark runs (both
    allowlists, both arms). Method: [docs/method.md](docs/method.md#the-detector-on-real-final-messages).

## Why

Opus 5.5 and Sonnet 5.5 report progress as they work, and some of those reports end the turn.
Anthropic's own [prompting guide](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5#unattended-agentic-runs)
lists the four ways it happens. In an interactive session you type "continue". In a headless run or
an overnight job nobody types anything, and you come back to a summary that ends with "Want me to
continue with the remaining three?" or "Once you approve it, I'll run `python -m pytest -q`."

## Install

```
claude plugin marketplace add Arthur031221/cliffhanger && claude plugin install cliffhanger@cliffhanger
```

That installs the hook, the skill, and a `/cliffhanger:stats` command. Other ways in:

| You want | Run |
|---|---|
| The skill only, for any agent that reads Agent Skills | `npx skills add Arthur031221/cliffhanger -g` |
| The hook in `~/.claude/settings.json`, no plugin | `git clone https://github.com/Arthur031221/cliffhanger && cliffhanger/bin/cliffhanger install` |
| One session, from a clone | `claude --plugin-dir ./cliffhanger` |
| Codex, Cursor, OpenCode (no hook) | copy [AGENTS.md](AGENTS.md) into your project |

Python 3.8 or newer must be on `PATH` as `python3`. No other dependencies.

## Quick start

See the hook decide, without starting an agent:

```
git clone https://github.com/Arthur031221/cliffhanger && cd cliffhanger
echo '{"session_id":"try","last_assistant_message":"Two of five call sites migrated. Want me to continue with the rest?"}' | python3 hooks/cliffhanger.py
bin/cliffhanger stats
```

The first command prints a `{"decision": "block", ...}` object naming the pattern it caught. The
second prints `caught 1 early stop this week in 1 of 1 sessions`.

For unattended runs, put the skill in the system prompt from the first request, which is where the
guide says this kind of instruction belongs. In our one run with the plugin loaded, the model did not
invoke the skill on its own for a two-part task:

```
claude -p "Migrate the five fetch() call sites to fetch_v2, update their tests, run pytest" \
  --append-system-prompt-file cliffhanger/SKILL.md --permission-mode acceptEdits
```

## How it works

On every `Stop` and `SubagentStop` event Claude Code sends the hook a JSON payload with
`last_assistant_message`, `transcript_path`, `stop_hook_active`, and `background_tasks`. The hook
decides in this order and logs every decision to `~/.cliffhanger/log.jsonl`:

| Order | Condition | Decision |
|---|---|---|
| 1 | The message contains `BLOCKED:` or `NEEDS-YOU:` | allow |
| 2 | Background tasks are still running (they wake the session when done) | allow |
| 3 | Permission mode is `plan` | allow |
| 4 | This user turn already had 3 automatic continuations (`CLIFFHANGER_MAX`) | allow |
| 5 | The agent's checklist has open items | block: "Open items: ... Continue with them." |
| 6 | A checklist exists and every item is done | allow |
| 7 | No checklist, and the message names a blocker ("cannot proceed without", "credentials") | allow |
| 8 | No checklist, and the message matches an early-stop pattern | block, naming the pattern |
| 9 | Anything else | allow |

The checklist comes from the transcript: `TaskCreate` and `TaskUpdate` calls, the latest `TodoWrite`
list, or the latest Markdown `- [ ]` list the agent wrote in this user turn. The Markdown fallback
matters because Opus 5.5 and Sonnet 5.5 ship without todo tools by default. Claude Code writes the
transcript asynchronously, so the hook first waits (up to 1.5 s) for `last_assistant_message` to
reach the file. Without that wait, an item ticked in the final message could still read as open.

The regex bank is only a fallback for when there is no checklist. It covers the guide's four
patterns plus one we saw in our own runs: a report that the work was never tested. When a checklist
exists it wins. "All done. Want me to also add CI?" after a finished checklist is allowed, not
turned into scope creep.

The counter resets when `stop_hook_active` is false, which is how Claude Code marks a fresh user
turn. Claude Code's own cap of 8 consecutive blocks (`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`) stays behind
it. The hook never calls a model, uses only the standard library, and allows the stop on any internal
error (logged to `~/.cliffhanger/errors.log`).

The skill is the other half. The hook can only send the agent back. The skill tells it what done
means, to keep a checklist the hook can read, to put status notes in the same message as the next
tool call, and how to write a blocker. [docs/method.md](docs/method.md) has the full detector, the
end-to-end transcripts, and the benchmark method.

## The four cliffhangers

From Anthropic's [Prompting Claude Opus 5.5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5#unattended-agentic-runs),
quoted, with the rule id the hook logs:

| The guide's words | Rule | What the agent writes instead |
|---|---|---|
| "a long summary of what was done that closes by announcing the next step and has no tool call" | `announces-next-step` | the status note and the next tool call in one message |
| "an offer to carry on with something unless the user would prefer otherwise" | `offers-to-continue` | the rest of the work |
| "a list of decisions for the user when, by your own account, none of them blocks the rest of the work" | `decisions-for-user` | the calls it made and why, then more work |
| "deciding that this is a good place to report, because the turn has been long or a milestone is done" | `good-place-to-report` | a one-line status note, then more work |
| (ours) a report that the work was never run or tested | `leaves-work-unverified` | the test run, or a `BLOCKED:` line saying why it can't |

## `cliffhanger stats`

```
$ cliffhanger stats
caught 2 early stops this week in 2 of 4 sessions
     1  offered to continue
     1  ended with the work untested
allowed 2 stops
     1  BLOCKED: or NEEDS-YOU: named
     1  checklist complete
```

That output is from the demo above. `--days 30` widens the window, `--json` prints the numbers. Inside
Claude Code, `/cliffhanger:stats` runs the same thing.

## Comparison

| | Runs inside the session | Reads the agent's checklist | Escape for real blockers | Continuation cap | Ships instructions | Published measurement | Model calls per stop |
|---|---|---|---|---|---|---|---|
| **cliffhanger** | Stop and SubagentStop hook | TaskCreate/TaskUpdate, TodoWrite, Markdown `- [ ]` | `BLOCKED:` / `NEEDS-YOU:` lines | 3 per user turn | SKILL.md, AGENTS.md | [bench/results.md](bench/results.md) | 0 |
| [`/goal`](https://code.claude.com/docs/en/goal) (built in) | prompt-based Stop hook | no, a small model judges a condition you write | the evaluator can rule the goal impossible | stops after several turns with no tool use | no | no | 1 (Haiku by default) |
| [claude-nonstop](https://github.com/garetneda-gif/claude-nonstop) | two Stop hooks | TaskCreate/TaskUpdate/TodoWrite | a `STATUS: DONE` report and a deactivate file | 20 by default (opt-in guard) | no | none found | 0 |
| [no-cliffhanger](https://github.com/waitdeadai/no-cliffhanger) | Stop and SubagentStop hook, bash and jq | no, the last 320 characters of the message | `Status: blocked` endings, explicit y/n questions | not stated | no | none found | 0 |
| [ralph-claude-code](https://github.com/frankbria/ralph-claude-code) and other Ralph loops | no, an outer loop that restarts `claude` | its own fix plan | an `EXIT_SIGNAL` in the output | rate limit and circuit breaker | yes | none found | a new session per loop |

`/goal` is the right tool when you can state the end condition ("all tests in test/auth pass"). It is
per session and you type it each time. cliffhanger is always on, costs no model calls, and reads the
checklist the agent already keeps. claude-nonstop is the closest design and reads the same task
tools. Its scripts (checked 2026-09-30) read only the task tools, so they see no checklist on a 5.5
model without todo tools, and they read the transcript without waiting for it to catch up.
Ralph loops restart whole sessions, which is heavier and loses in-session context.

## Reference

### Commands

| Command | What it does |
|---|---|
| `cliffhanger stats [--days N] [--json]` | Early stops caught, by pattern, and stops allowed, by reason. Default window 7 days. |
| `cliffhanger status [--settings PATH] [--json]` | On or off, installed in which events, mode, cap, log path. |
| `cliffhanger off` / `cliffhanger on` | Pause or resume the hook everywhere (creates or removes `~/.cliffhanger/off`). |
| `cliffhanger install [--settings PATH] [--no-subagent] [--dry-run] [--json]` | Add Stop and SubagentStop handlers to `~/.claude/settings.json`. Backs the file up first, keeps every existing hook, follows a symlinked settings file, writes atomically. Idempotent. |
| `cliffhanger uninstall [--settings PATH] [--dry-run] [--json]` | Remove only handlers that point at `cliffhanger.py`, with a backup. |

Every command takes `--help`.

### Environment

| Variable | Default | Effect |
|---|---|---|
| `CLIFFHANGER_MAX` | `3` | Automatic continuations per user turn before the hook lets the stop through. The guide suggests two or three. |
| `CLIFFHANGER_OBSERVE` | unset | `1` logs what would be blocked and never blocks. Use it to measure your own sessions first. |
| `CLIFFHANGER_DISABLE` | unset | `1` skips the hook for that process tree. |
| `CLIFFHANGER_SYNC_MS` | `1500` | Longest wait for the transcript to catch up with the final message. |
| `CLIFFHANGER_HOME` | `~/.cliffhanger` | Log, state, and off switch location. |

### Files

- `~/.cliffhanger/log.jsonl`: one line per decision with `ts`, `session`, `event`, `agent`, `action`,
  `observe`, `rule`, `open` (open item texts), `match` (the phrase that matched), `source`
  (`tasks`, `todo`, `markdown`, or null), `continuation`, `cwd`. No message text beyond those.
- `~/.cliffhanger/state/`: per-session continuation counters and short-lived dedupe locks.
- `~/.cliffhanger/errors.log`: exceptions the hook swallowed while failing open.

### What the agent receives

With open items:

```
Open items: test in tests/test_api.py; CHANGELOG.md line under Unreleased. Continue with them. If one is blocked, say what is blocking it on a line that starts with BLOCKED:.
```

With a pattern match, the reason names the pattern and quotes the phrase, then gives the same way
out: do the work, end with a plain final report if everything is done, or write a `BLOCKED:` line.

## Limits and FAQ

**Does the hook make the model finish?** Not by itself. In the benchmark the skill did the work and
the hook never had to block. In our one real block, in an end-to-end run without the skill, the
agent went back, tried another test command, got refused again, and ended with a proper `BLOCKED:`
line. It never found the allowed `pytest`. The hook turned a vague stop into a clear one, which is
what you want at 3 a.m., but it is not the same as finishing.

**Is it worth it on every task?** With every command it needed allowed, Sonnet 5.5 finished all 12
benchmark tasks either way and the skill added 13 percent to cost. Run `CLIFFHANGER_OBSERVE=1` for a
week, then read `cliffhanger stats` before you turn blocking on.

**Interactive sessions.** The guide says to leave this kind of instruction out when someone is
there to answer. The hook still helps with open checklist items. If it gets in your way,
`cliffhanger off` pauses it, and `CLIFFHANGER_OBSERVE=1` keeps the log without blocking.

**"Stop hook error occurred".** Claude Code labels every `decision: "block"` from a Stop hook that
way in the transcript. It is the label, not a failure. Real failures go to `~/.cliffhanger/errors.log`.

**English only.** The regex bank matches English phrasing. The checklist path works in any language.

**AGENTS.md is read from parent directories.** Claude Code loaded this repo's `AGENTS.md` into a
session running in a subdirectory. If you copy it into a monorepo, every session below it gets it.

**Other agents.** Codex, Cursor, and OpenCode get `AGENTS.md`, which is instructions only. Nothing
enforces it there yet.

**Privacy.** The hook reads your transcript locally and writes only the fields listed under Files.
It makes no network calls.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). New patterns need a real transcript excerpt that must block
and a real final report that must still pass.

## License

MIT. See [LICENSE](LICENSE).
