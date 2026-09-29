# Method

How the detector decides, how it was tested, what happened in real headless sessions, and how the
benchmark was run. Everything here was measured on one machine (MacBook Air M5, 24 GB) with Claude
Code 2.1.284 and `claude-sonnet-5-5` at its default effort, on 2026-09-30.

## The detector

`hooks/cliffhanger.py` runs on `Stop` and `SubagentStop`. It reads these fields from the payload
(names from the [hooks reference](https://code.claude.com/docs/en/hooks)): `last_assistant_message`,
`transcript_path` (or `agent_transcript_path` for a subagent), `stop_hook_active`, `session_id`,
`agent_id`, `agent_type`, `background_tasks`, `permission_mode`.

Decision order. The first rule that applies wins.

| # | Rule id | Condition | Decision |
|---|---|---|---|
| 1 | `blocker-token` | `BLOCKED:` or `NEEDS-YOU:` (uppercase) anywhere in the last message | allow |
| 2 | `background-work` | `background_tasks` is non-empty | allow |
| 3 | `plan-mode` | `permission_mode` is `plan` | allow |
| 4 | `max-continuations` | this user turn already had `CLIFFHANGER_MAX` blocks (default 3) | allow |
| 5 | `open-items` | the checklist has items not `completed` or `deleted` | block |
| 6 | `checklist-done` | a checklist exists and all items are done | allow |
| 7 | `blocker-phrase` | no checklist, and the message names a blocker in prose | allow |
| 8 | pattern rules | no checklist, and one of five regexes matches | block |
| 9 | `no-pattern` | nothing above applied | allow |

Rule 2 follows the guide's advice: work the model started in the background will wake the session
when it finishes, so the stop is a wait, not an exit. Rule 4 follows the guide's "stop after two or
three automatic continuations on the same task". The counter lives in
`~/.cliffhanger/state/<session>.json` and resets whenever `stop_hook_active` is false, which Claude
Code sets on a fresh user turn. Claude Code's own cap of eight consecutive blocks
(`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`) stays in place behind it.

### The checklist

Rebuilt from the transcript on every stop, in the record shapes Claude Code 2.1.284 writes:

- `TaskCreate` tool calls. The id comes from the tool result's `toolUseResult.task.id`, or from
  `Task #N created` in the result text. Failed creates are ignored.
- `TaskUpdate` calls with `taskId` and `status`. `deleted` counts as done.
- The latest `TodoWrite` call's `todos` list, when `CLAUDE_CODE_ENABLE_TASKS=0` selects it.
- Otherwise the latest Markdown list of `- [ ]` and `- [x]` lines in an assistant message. This
  matters because the task tools are off by default on Opus 5.5 and Sonnet 5.5
  ([tools reference](https://code.claude.com/docs/en/tools-reference#task-tool-availability)).
  A Markdown list expires when a new prompt arrives (`turnOrigin` of `human`, `sdk`, or
  `scheduled`), but not on a background-task notification.

Records with `isSidechain: true` are skipped. The hooks reference warns that the transcript "is
written asynchronously and may lag". A checklist item ticked just before the final message could
still read as open. So the hook first polls the file (every 100 ms, up to `CLIFFHANGER_SYNC_MS`,
default 1500) until the last 40 characters of `last_assistant_message` appear in it.

When a checklist exists it is the only signal. The regexes never override it in either direction.

### The regex bank

Used only without a checklist. Four rules follow the four early stops in Anthropic's
[Prompting Claude Opus 5.5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5#unattended-agentic-runs)
guide. The fifth comes from our own end-to-end runs (below).

| Rule id | Guide's wording | Example phrases |
|---|---|---|
| `announces-next-step` | "a long summary of what was done that closes by announcing the next step" | "the next step is", "next, I'll", "I'll run", "what's left" |
| `offers-to-continue` | "an offer to carry on with something unless the user would prefer otherwise" | "want me to", "would you like me to", "shall I", "once you approve" |
| `decisions-for-user` | "a list of decisions for the user when ... none of them blocks the rest of the work" | "a few decisions for you", "which approach would you prefer", an `Options:` line |
| `good-place-to-report` | "deciding that this is a good place to report" | "good stopping point", "natural place to pause", "in the next turn" |
| `leaves-work-unverified` | (ours) | "couldn't run the tests", "unverified", "untested" |

Blocker phrases that suppress a pattern block: "need your", "cannot proceed", "credentials", "API
key", "access token", "permission denied", "which one of these", "destructive", "irreversible",
"requires approval", "protected branch". A blocker phrase never overrides open checklist items.
Only the explicit token does.

### Failure behaviour

Any exception is written to `~/.cliffhanger/errors.log` and the hook exits 0 with no output, so the
stop goes through. When the plugin and a `settings.json` install are both active, Claude Code runs
both copies (it deduplicates identical handlers only across settings files). The first copy to
create `~/.cliffhanger/state/<digest>.lock` decides and the second exits silently.

## Tests on synthetic transcripts

`tests/test_hook.py` runs the hook as a subprocess against transcripts built by
`tests/conftest.py`, whose record shapes were copied from real 2.1.284 transcripts (probes run with
`CLAUDE_CODE_ENABLE_TODO_TOOLS=1`, and with `CLAUDE_CODE_ENABLE_TASKS=0` for `TodoWrite`). Every
rule has at least one test, and the block rules have allow-path counterparts. Also covered:
observe mode, the counter and its reset, the off switch, subagent transcripts, internal subagents
with an empty `agent_type`, duplicate copies, a transcript flushed 400 ms after the hook starts,
malformed input, and a missing transcript. `tests/test_cli.py` covers `install` and `uninstall`
against existing hooks, invalid JSON, wrong shapes, symlinked settings files, and dry runs.

No precision or recall figure is claimed from these tests. The same person wrote the patterns and
the examples.

## End-to-end headless sessions (observed behaviour)

Fixture: three files (`pricing.py`, `cart.py`, `invoice.py`) with a hard-coded 20 percent tax
rate and a two-test suite, in a git repo under the session scratch directory. Task, identical in
every run:

> Two parts. Part 1: add a discount(price, pct) function to pricing.py that raises ValueError
> unless 0 <= pct <= 100, with tests in test_pricing.py. Part 2: replace every hard-coded 20% tax
> rate (1.2 and 0.2) in pricing.py, cart.py and invoice.py with a TAX_RATE constant defined in
> pricing.py, and add tests for cart_summary and invoice_lines in test_pricing.py. Run pytest at
> the end.

Command shape:

```
env -u CLAUDECODE claude -p "$TASK" --model claude-sonnet-5-5 --output-format stream-json --verbose \
  --permission-mode acceptEdits --allowedTools "Read,Edit,Write,Bash(pytest *)" \
  [--settings <hook settings> | --plugin-dir <this repo>]
```

| Run | Setup | Tests run by the agent | Hook decisions | End of the run |
|---|---|---|---|---|
| base | hook in observe mode | no | allow `no-pattern` | "Once you approve it, I'll run `python -m pytest -q`" |
| treat | plugin via `--plugin-dir` (skill listed, never invoked) | yes, `pytest -q`, 8 passed | allow `no-pattern` | finished |
| hook1 | blocking hook, first regex bank | no | allow `no-pattern` | "the tests are unverified" |
| hook2 | blocking hook, first regex bank | no | allow `no-pattern` | "the tests are unverified" |
| hook3 | blocking hook, current bank | no | allow `blocker-phrase` ("needs approval") | "The code and tests are written but haven't been run" |
| hook4 | blocking hook, current bank | no | block `announces-next-step`, then allow `blocker-token` | a `BLOCKED:` line |

What happened in all six: the agent wrote the files with one Bash heredoc, which Claude Code
refused ("Contains brace with quote character (expansion obfuscation)"). Every run recovered by
switching to the Write tool. Then it ran `python -m pytest -q`, which the allowlist does not cover,
and was refused twice. Five of six runs never tried the plain `pytest` command the allowlist did
permit, and all five ended with the tests never run: three with a vague closing line, `hook3` with
a prose blocker the hook allowed, and `hook4` with an explicit `BLOCKED:` line after the hook sent
it back. Only `treat` ran `pytest -q` and finished.

The first two blocking runs exposed a gap. Their final messages ("I couldn't run pytest ... So the
tests are unverified") matched none of the four guide patterns, so the hook let them through. That
is where the fifth rule, `leaves-work-unverified`, and the "I'll run" and "once you approve" phrases
came from. The skill gained one line for the same case: an allowed command that does the same job
as a denied one is not a blocker.

`hook4`, verbatim from the stream. The agent's first end of turn:

```
Both parts are written, but I couldn't run pytest. The permission system blocked every attempt, so
the tests haven't been run.
...
To run the tests yourself, use `python -m pytest -q` in the project directory, or approve the
command and I'll run it.
```

What Claude Code delivered back to the agent (the stream also carried a `stop-hook-error`
notification, which is how Claude Code labels any `decision: "block"`):

```
Stop hook feedback:
Your last message ended the turn with a summary that announces the next step instead of taking it
("I'll run"). If work the user asked for is still owed, do it now instead of describing or offering
it. If everything asked for is done, end with the final report and no offer. If something only the
user can clear is in the way, write BLOCKED: <what> <what you need> on its own line.
```

The agent's next action was a tool call, `python3 -m pytest -q`, refused again. Then it ended
with:

```
The code changes for both parts are in place, but the tests haven't run.

BLOCKED: pytest can't run because the sandbox requires approval for `python -m pytest` and
`python3 -m pytest`, and I can't grant it. Approve the command, or run `python3 -m pytest -q` in
the project directory.
```

The hook allowed that stop (`blocker-token`, continuation 1). The hook did not make the agent find
`pytest`. It turned a vague "I'll run it once you approve" into an explicit blocker line that names
the command and the ask. The skill line added afterwards targets the missing step.

Two more observations from these runs:

- **The skill did not trigger on its own.** With `--plugin-dir`, `cliffhanger:cliffhanger` was in
  the session's skill list but the agent never invoked it for this task. For unattended runs, put
  the skill in the system prompt with `--append-system-prompt-file`, which is also where the
  guide says its paragraph belongs. The hook enforces either way.
- **AGENTS.md leaks from parent directories.** The first benchmark attempt put run directories
  inside this repository. The baseline transcript contained the text of this repo's `AGENTS.md`,
  loaded from a parent directory, and its final report copied the skill's format. That run was
  discarded after three minutes. `bench/run.sh` now refuses an output directory inside the repo
  or below an `AGENTS.md` or `CLAUDE.md`.

## Benchmark

### Setup

- **Fixture:** `bench/fixture/`, a 150-line WSGI book inventory (`shelf`) with a store, a JSON API,
  a CLI, `docs/api.md`, `README.md`, `CHANGELOG.md`, and 7 passing tests. Standard library only.
- **Tasks:** `bench/tasks.json`, 12 tasks. Each asks for 4 to 6 parts: code, tests, a docs or
  README entry, a changelog line under `## Unreleased`, and "run pytest and make sure the whole
  suite passes".
- **Checks:** `bench/score.py` scores each task with 5 to 8 deterministic checks (regex on named
  files, the `## Unreleased` section, and its own `pytest` run with a minimum test count). A task is
  done when every check passes.
- **Arms:** same hook in both. Baseline: `CLIFFHANGER_OBSERVE=1`, no skill. Treatment: blocking
  hook plus `SKILL.md` (frontmatter stripped) through `--append-system-prompt-file`.
- **Runs:** each arm in its own fresh copy of the fixture outside the repository, baseline and
  treatment of the same task in parallel (two sessions at a time), n=1 per task and arm. If a run
  ended with checks failing, it was resumed with `claude -p "continue" --resume <id>`, at most 3
  times.
- **Command** (from `bench/run.sh`):

  ```
  env -u CLAUDECODE [-u other CLAUDE_CODE_* session variables] CLIFFHANGER_HOME=<run>/home \
    claude -p "<task>" --model claude-sonnet-5-5 --output-format json \
    --settings <run>/settings.<arm>.json --permission-mode acceptEdits \
    --allowedTools "<TOOLS>" --max-turns 80 [--append-system-prompt-file skill-body.md]
  ```

### Metrics

- **Work owed at first stop:** the first `claude -p` invocation ended and at least one check failed.
- **Ran suite green before first stop:** the session transcript has a Bash `pytest` call whose
  result says `passed` with no failures, before the first Stop event.
- **Nudges:** `continue` resumes needed to reach done.
- **Cost:** `total_cost_usd` from the last invocation's JSON (Claude Code reports it cumulatively
  across `--resume`). A client-side estimate.
- **Output tokens:** summed from the session transcript, one count per API message id.

### Condition A: permissive test allowlist

`TOOLS="Read,Edit,Write,Glob,Grep,Bash(pytest *),Bash(python -m pytest *),Bash(python3 -m pytest *)"`.
The allowlist covers every test command the agent tried in the end-to-end runs, so this condition
measures early stopping without the permission trap.

| Arm | Tasks | Work owed at first stop | Ran suite green before first stop | Nudges | Hook blocks | Cost USD | Output tokens |
|---|---|---|---|---|---|---|---|
| baseline | 12 | 0 | 12 | 0 | 0 (0 would-block in observe mode) | 1.56 | 47,503 |
| treatment | 12 | 0 | 12 | 0 | 0 | 1.77 | 47,940 |

Sonnet 5.5 finished all 12 tasks in one invocation in both arms. The hook never needed to block.
The detector allowed all 12 real baseline final reports, so it produced no false block on them.
The treatment cost 13 percent more ($0.21 over 12 tasks) for no measured gain on these tasks. Most
of that cost comes from the extra system prompt and the checklist messages, since output tokens
barely moved (+0.9 percent). Every treatment run wrote the Markdown checklist the skill asks for,
and the hook read it (`checklist-done` on all 12 stops).

On short, well-specified tasks with the tools it needs, Sonnet 5.5 did not stop early in this
sample. Every early stop we observed, here and in condition B, followed a refused tool call.

### Condition B: the brief's allowlist

`TOOLS="Read,Edit,Write,Bash(pytest *)"`, the command line from the original plan. The harness
refuses `python -m pytest`, which is the form the agent reaches for first.

| Arm | Tasks | Work owed at first stop (file checks) | Ran suite green before first stop | Nudges | Hook blocks | Cost USD | Output tokens |
|---|---|---|---|---|---|---|---|
| baseline | 12 | 0 | 6 | 0 | 0 (6 would-block in observe mode) | 1.67 | 50,228 |
| treatment | 12 | 0 | 12 | 0 | 0 | 1.74 | 43,629 |

The code, tests, docs, and changelog lines were complete in all 24 runs. What was owed was the
last part of every task, "run pytest and make sure the whole suite passes". In 6 of 12 baseline
runs the agent tried only `python -m pytest`, was refused, and ended its turn without running the
suite. The other 6 fell back to `pytest` and ran it. In the treatment every run ran the suite green
before stopping, and the hook never blocked, because every run kept the skill's Markdown checklist
and ticked the test item only after the run. The skill did the work in this condition. The cost
was 4 percent more, with 13 percent fewer output tokens.

This condition is not a held-out test. The skill line about allowed equivalents of a denied command
and the `leaves-work-unverified` rule were written after the end-to-end runs showed the same
failure on another fixture.

### The detector on real final messages

The regex bank alone, applied to the first final message of all 48 benchmark runs (run2 and run4,
both arms), against "the agent ran the suite green before its first stop": it flagged 6 messages,
all 6 from runs that had skipped the suite, and none of the 42 others. Per-run detail is in
[bench/results.md](../bench/results.md#detector-on-real-final-messages). The sample is one model,
one fixture, and some of the phrases were added after seeing this failure mode.

### Threats to validity

- n=1 per task and arm. A different day or effort level could move any single row.
- The tasks are short (10 to 28 turns) and fully specified. The guide describes early stops on long
  tasks, which this benchmark does not cover.
- One model (Sonnet 5.5) on one fixture. Opus 5.5 was not run.
- The treatment gets the skill through the system prompt. With the plugin alone, the skill may not
  be invoked at all (see the end-to-end runs).
- Raw run directories for run2 and the end-to-end runs were lost when the scratch directory they
  lived in was wiped by something outside this project. Their tables were printed before that and
  are reproduced as printed. Run4's raw summary and hook log are committed in `bench/raw/`.
