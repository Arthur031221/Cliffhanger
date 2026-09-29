# Benchmark results

Raw tables from `bench/score.py summarize`, copied as printed. Method and metric definitions are in
[docs/method.md](../docs/method.md#benchmark).

Common to every run: MacBook Air M5 (24 GB), macOS 26, Claude Code 2.1.284, `claude-sonnet-5-5` at
default effort, n=1 per task and arm, baseline and treatment of the same task run in parallel, at
most 3 `continue` nudges, 2026-09-30.

## Run history

| Run | Start (local) | Allowlist | Status |
|---|---|---|---|
| run1 | 00:33 | permissive (condition A) | Discarded after 3 minutes. Run directories were inside this repo, and Claude Code loaded the repo's `AGENTS.md` into the baseline from a parent directory. |
| run2 | 00:36 | permissive (condition A) | Complete, 12 of 12 tasks. Table below. The run directories were later lost when the scratch directory holding them was wiped by something outside the benchmark. The table was printed by `score.py` before that. The session transcripts survive in `~/.claude/projects`. |
| run3 | 00:46 | `Read,Edit,Write,Bash(pytest *)` (condition B) | Lost in the same wipe at about 00:52. t01 to t04 had finished as done in one invocation in both arms. t08 to t12 failed to start ("Settings file not found"). Not used. |
| run4 | see below | `Read,Edit,Write,Bash(pytest *)` (condition B) | See below. |

Hook versions: run2 used commit `044488e`, run4 used commit `d8eb2bb`. The difference is the
transcript scan (performance) and regex line layout. Three alternatives were dropped from the bank
in between ("should I move on", "should I start", "before I go further").

## Condition A: permissive test allowlist (run2)

`--allowedTools "Read,Edit,Write,Glob,Grep,Bash(pytest *),Bash(python -m pytest *),Bash(python3 -m pytest *)"`

| arm | task | checks after 1st stop | agent ran suite green before 1st stop | final | nudges | turns | cost USD | output tokens | hook decisions |
|---|---|---|---|---|---|---|---|---|---|
| baseline | t01-health | 5/5 | True | 5/5 | 0 | 14 | 0.0921 | 2640 | allow:no-pattern |
| baseline | t02-isbn | 6/6 | True | 6/6 | 0 | 12 | 0.1374 | 4286 | allow:no-pattern |
| baseline | t03-pagination | 6/6 | True | 6/6 | 0 | 12 | 0.1339 | 4485 | allow:no-pattern |
| baseline | t04-patch | 6/6 | True | 6/6 | 0 | 16 | 0.1599 | 5558 | allow:no-pattern |
| baseline | t05-stats-cli | 6/6 | True | 6/6 | 0 | 12 | 0.1168 | 3459 | allow:no-pattern |
| baseline | t06-rename-year | 8/8 | True | 8/8 | 0 | 15 | 0.1123 | 2953 | allow:no-pattern |
| baseline | t07-search | 6/6 | True | 6/6 | 0 | 14 | 0.1274 | 3630 | allow:no-pattern |
| baseline | t08-persistence | 7/7 | True | 7/7 | 0 | 13 | 0.1503 | 4696 | allow:no-pattern |
| baseline | t09-validation | 6/6 | True | 6/6 | 0 | 15 | 0.1257 | 3505 | allow:no-pattern |
| baseline | t10-tags | 7/7 | True | 7/7 | 0 | 16 | 0.1403 | 4662 | allow:no-pattern |
| baseline | t11-error-helper | 7/7 | True | 7/7 | 0 | 11 | 0.1221 | 3410 | allow:no-pattern |
| baseline | t12-export | 6/6 | True | 6/6 | 0 | 14 | 0.1377 | 4219 | allow:no-pattern |
| treatment | t01-health | 5/5 | True | 5/5 | 0 | 14 | 0.1142 | 2701 | allow:checklist-done |
| treatment | t02-isbn | 6/6 | True | 6/6 | 0 | 17 | 0.1790 | 5218 | allow:checklist-done |
| treatment | t03-pagination | 6/6 | True | 6/6 | 0 | 10 | 0.1389 | 3765 | allow:checklist-done |
| treatment | t04-patch | 6/6 | True | 6/6 | 0 | 16 | 0.1662 | 5295 | allow:checklist-done |
| treatment | t05-stats-cli | 6/6 | True | 6/6 | 0 | 11 | 0.1353 | 3599 | allow:checklist-done |
| treatment | t06-rename-year | 8/8 | True | 8/8 | 0 | 22 | 0.1728 | 4048 | allow:checklist-done |
| treatment | t07-search | 6/6 | True | 6/6 | 0 | 12 | 0.1261 | 2933 | allow:checklist-done |
| treatment | t08-persistence | 7/7 | True | 7/7 | 0 | 21 | 0.1595 | 4798 | allow:checklist-done |
| treatment | t09-validation | 6/6 | True | 6/6 | 0 | 11 | 0.1411 | 3641 | allow:checklist-done |
| treatment | t10-tags | 7/7 | True | 7/7 | 0 | 16 | 0.1650 | 4574 | allow:checklist-done |
| treatment | t11-error-helper | 7/7 | True | 7/7 | 0 | 10 | 0.1235 | 3136 | allow:checklist-done |
| treatment | t12-export | 6/6 | True | 6/6 | 0 | 13 | 0.1459 | 4232 | allow:checklist-done |

| arm | tasks run | done at first stop | work owed at first stop | ran suite green before 1st stop | done after nudges | nudges | hook blocks | total cost USD | output tokens | errors |
|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 12 | 12 | 0 | 12 | 12 | 0 | 0 | 1.56 | 47503 | 0 |
| treatment | 12 | 12 | 0 | 12 | 12 | 0 | 0 | 1.77 | 47940 | 0 |

Reading: no early stop in either arm, so nothing for the hook to catch. Treatment cost +13.5
percent, output tokens +0.9 percent, turns 173 against 179.

## Condition B: the brief's allowlist (run4)

`--allowedTools "Read,Edit,Write,Bash(pytest *)"`. Everything else as in condition A. Started
00:53:47, finished 01:01:29. Raw summary, hook log, and metadata: [raw/](raw/).

| arm | task | checks after 1st stop | agent ran suite green before 1st stop | final | nudges | turns | cost USD | output tokens | hook decisions |
|---|---|---|---|---|---|---|---|---|---|
| baseline | t01-health | 5/5 | True | 5/5 | 0 | 16 | 0.1023 | 2293 | allow:no-pattern |
| baseline | t02-isbn | 6/6 | True | 6/6 | 0 | 13 | 0.1401 | 4133 | allow:no-pattern |
| baseline | t03-pagination | 6/6 | False | 6/6 | 0 | 12 | 0.1252 | 3910 | block:leaves-work-unverified |
| baseline | t04-patch | 6/6 | False | 6/6 | 0 | 16 | 0.1590 | 5561 | block:announces-next-step |
| baseline | t05-stats-cli | 6/6 | False | 6/6 | 0 | 13 | 0.1138 | 3139 | block:announces-next-step |
| baseline | t06-rename-year | 8/8 | True | 8/8 | 0 | 21 | 0.1403 | 3530 | allow:no-pattern |
| baseline | t07-search | 6/6 | True | 6/6 | 0 | 15 | 0.1276 | 3230 | allow:no-pattern |
| baseline | t08-persistence | 7/7 | False | 7/7 | 0 | 14 | 0.1432 | 4522 | block:leaves-work-unverified |
| baseline | t09-validation | 6/6 | True | 6/6 | 0 | 17 | 0.1818 | 6542 | allow:no-pattern |
| baseline | t10-tags | 7/7 | False | 7/7 | 0 | 19 | 0.1557 | 4810 | block:leaves-work-unverified |
| baseline | t11-error-helper | 7/7 | False | 7/7 | 0 | 13 | 0.1345 | 4422 | block:leaves-work-unverified |
| baseline | t12-export | 6/6 | True | 6/6 | 0 | 16 | 0.1472 | 4136 | allow:no-pattern |
| treatment | t01-health | 5/5 | True | 5/5 | 0 | 16 | 0.1154 | 2299 | allow:checklist-done |
| treatment | t02-isbn | 6/6 | True | 6/6 | 0 | 12 | 0.1453 | 3874 | allow:checklist-done |
| treatment | t03-pagination | 6/6 | True | 6/6 | 0 | 13 | 0.1558 | 4208 | allow:checklist-done |
| treatment | t04-patch | 6/6 | True | 6/6 | 0 | 16 | 0.1696 | 4976 | allow:checklist-done |
| treatment | t05-stats-cli | 6/6 | True | 6/6 | 0 | 13 | 0.1298 | 3083 | allow:checklist-done |
| treatment | t06-rename-year | 8/8 | True | 8/8 | 0 | 20 | 0.1671 | 3543 | allow:checklist-done |
| treatment | t07-search | 6/6 | True | 6/6 | 0 | 13 | 0.1390 | 3465 | allow:checklist-done |
| treatment | t08-persistence | 7/7 | True | 7/7 | 0 | 21 | 0.1389 | 4079 | allow:checklist-done |
| treatment | t09-validation | 6/6 | True | 6/6 | 0 | 11 | 0.1420 | 3722 | allow:checklist-done |
| treatment | t10-tags | 7/7 | True | 7/7 | 0 | 28 | 0.1669 | 4425 | allow:checklist-done |
| treatment | t11-error-helper | 7/7 | True | 7/7 | 0 | 10 | 0.1186 | 2736 | allow:checklist-done |
| treatment | t12-export | 6/6 | True | 6/6 | 0 | 20 | 0.1473 | 3219 | allow:checklist-done |

| arm | tasks run | done at first stop | work owed at first stop | ran suite green before 1st stop | done after nudges | nudges | hook blocks | total cost USD | output tokens | errors |
|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 12 | 12 | 0 | 6 | 12 | 0 | 6 | 1.67 | 50228 | 0 |
| treatment | 12 | 12 | 0 | 12 | 12 | 0 | 0 | 1.74 | 43629 | 0 |

Reading:

- **Deliverables:** complete in all 24 runs, so no nudges were needed and "work owed at first stop"
  by the file checks is 0 in both arms.
- **Verification:** every task says "Run pytest and make sure the whole suite passes". In 6 of 12
  baseline runs the agent ended its turn without ever running the suite green. In every baseline run
  the harness refused `python -m pytest` (the allowlist covers only `pytest ...`), and those 6
  never tried the allowed form. The treatment ran the suite green before stopping in 12 of 12.
- **Hook:** in the baseline, observe mode flagged exactly the 6 runs that skipped the tests (4
  `leaves-work-unverified`, 2 `announces-next-step` on "I'll run") and allowed the 6 that ran them.
  In the treatment it never had to block: every run kept the Markdown checklist and ticked it off.
  The gain in this arm came from the skill.
- **Cost:** treatment $1.74 against $1.67 (+4 percent). Output tokens 43,629 against 50,228 (-13
  percent).
- **Not held out.** The skill line about using an allowed equivalent of a denied command, and the
  `leaves-work-unverified` rule, were written after the same failure showed up in the end-to-end
  runs on a different fixture (docs/method.md). Treat condition B as a replication of that
  observation on 12 new tasks, not as an independent test.

## Detector on real final messages

The regex bank alone (as if no checklist existed), applied to the first final message of every run
in run2 and run4, against "the agent ran the suite green before its first stop":

| Set | Messages | Ended without running the suite | Flagged | Correctly flagged | Flagged in error |
|---|---|---|---|---|---|
| run2 baseline | 12 | 0 | 0 | 0 | 0 |
| run2 treatment | 12 | 0 | 0 | 0 | 0 |
| run4 baseline | 12 | 6 | 6 | 6 | 0 |
| run4 treatment | 12 | 0 | 0 | 0 | 0 |
| total | 48 | 6 | 6 | 6 | 0 |

Same caveat: some phrases in the bank came from the end-to-end runs of this failure mode. 48
messages from one model on one fixture is a small sample.
