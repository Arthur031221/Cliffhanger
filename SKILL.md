---
name: cliffhanger
description: Use at the start of any task with more than one part. Keeps the agent working until every part is done or a real blocker is named. Never end a turn on a cliffhanger. Applies to unattended and headless runs, "do X, then Y, then Z" requests, migrations, refactors across several files, and any task that bundles code with tests, docs, or a changelog, even when the user never says "don't stop".
license: MIT
metadata:
  author: Arthur031221
  version: "0.1.0"
---

# cliffhanger

A message with no tool call ends your turn. In an unattended run nothing happens after that: the
work sits at 60 percent until a person comes back, reads your summary, and types "continue". That
round trip costs them minutes to hours and costs you the context you had loaded. This skill is the
set of rules for ending a turn only when ending it is the right call.

A Stop hook may be enforcing these rules. It reads your checklist and your last message, and it
sends you back to work if either says work is still owed. Section 6 covers what to do when that
happens.

## 1. What done means

A turn may end only when one of these is true:

- **(a) Every checklist item is completed**, and you checked it: the test ran green, the file
  exists, the command exited 0.
- **(b) A blocker exists that only the user can clear**, and you wrote it as a `BLOCKED:` line
  (section 5).
- **(c) The next action is destructive or irreversible** and needs the user's yes.

Nothing else ends a turn. These are not reasons to stop:

- The turn has been long. Length is not a milestone.
- One part is done and it feels like a natural checkpoint.
- You have a recommendation. Put it in a status note and keep going.
- You are unsure between two reasonable options that are cheap to reverse. Pick one, say which and
  why in one line, continue.
- A test failed. Debugging it is part of the task.
- Context is getting full. Claude Code compacts on its own. Keep your checklist current so nothing
  is lost when it does.

If the user asked you to stop after each step, check in, or wait for review, that instruction wins.
It is a stop they asked for, not a cliffhanger.

## 2. The four cliffhangers

Anthropic's guide [Prompting Claude Opus 5.5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5#unattended-agentic-runs)
names four ways the model ends a turn while work is still owed. Quoted from the guide:

> One: a long summary of what was done that closes by announcing the next step and has no tool
> call, so the next thing never starts. Two: an offer to carry on with something unless the user
> would prefer otherwise, which stops to wait for an answer the user was not going to give. Three:
> a list of decisions for the user when, by your own account, none of them blocks the rest of the
> work. Four: deciding that this is a good place to report, because the turn has been long or a
> milestone is done.

What each looks like, and what to write instead.

### One: the summary that announces the next step

Before, the turn ends here:

> Added `GET /health` to `app/api.py`. It returns `{"status": "ok", "version": "0.4.1"}`. Next I'll
> add a test in `tests/test_api.py` and document the endpoint in `docs/api.md`.

After, the note and the next action travel together:

> `GET /health` is in. Adding its test.
> *(Edit `tests/test_api.py` in the same message)*

If you can say what the next step is, you can take it.

### Two: the offer to carry on

Before:

> Two of the five call sites now use `fetch_v2`. Want me to continue with the remaining three?

After:

> Two of five call sites migrated. `billing.py` next.
> *(Edit `src/billing.py` in the same message)*

The user asked for all five. An offer to do what was already requested waits for an answer that
will not come.

### Three: the decision list that blocks nothing

Before:

> The parser is ported. A few decisions for you:
> 1. Keep the `--legacy` flag?
> 2. snake_case or camelCase for the new fields?
> 3. Should parse errors raise or return `None`?

After, make each call on the evidence, record it, and continue:

> Parser ported. Calls I made, each easy to reverse: kept `--legacy` as a hidden alias because
> `ci/nightly.sh` passes it, snake_case to match `models/`, parse errors raise `ParseError` like
> the old parser did. Updating the callers now.
> *(Edit `src/cli.py` in the same message)*

A decision blocks only when the options lead to different designs and the rest of the work depends
on which one is chosen. Then do every part that does not depend on it, and write a `NEEDS-YOU:`
line for the part that does.

### Four: the good place to report

Before:

> Phase 1 of the migration is complete and all 212 tests pass. This is a good checkpoint, so here
> is a summary of what changed so far: ...

After:

> Phase 1 done, 212 tests pass. Starting phase 2, the `orders` table.
> *(Bash `alembic revision -m "orders: add tenant_id"` in the same message)*

A milestone is a status note, not an exit.

## 3. Keep a live checklist

Create the checklist before the first edit. It is how you, the user, and the hook agree on what
"done" means.

- **One item per part the user asked for**, in their words, plus the parts the request implies:
  "tests pass" when you change code, a docs entry or changelog line when the repo keeps them and
  the request touches what they describe. Three to eight items fits most tasks. Do not split one
  edit into five items or pad the list with busywork.
- **Use the todo tool you have.** `TaskCreate` for each item and `TaskUpdate` as status changes,
  or `TodoWrite` with the whole list. On Opus 5.5 and Sonnet 5.5 neither tool is loaded by
  default. Then write the checklist as Markdown in the same message as your first tool call:

  ```
  - [ ] GET /health endpoint in app/api.py
  - [ ] test in tests/test_api.py, full suite green
  - [ ] docs/api.md entry
  - [ ] CHANGELOG.md line under Unreleased
  ```

  Repost it with `[x]` on finished items as you go, again in a message that carries a tool call.
- **Update after each item**, not in a batch at the end. The hook reads the checklist. A stale one
  either sends you back to work you finished or lets an unfinished turn end.
- **Completed means verified.** Written but not run is `in_progress`.
- **Scope changes go in the list.** Found a required migration: add an item. An item turned out to
  be unnecessary: delete it (`TaskUpdate` with status `deleted`, or drop the line) and say why in
  one line.

## 4. Status notes ride with the next tool call

Progress text goes in the same message as the next action, never alone. The note tells the user
what happened. The tool call keeps the turn alive.

Before, a message with no tool call, so the turn ends:

> Tests for the store are passing now. I'll move on to the API layer.

After:

> Store tests pass (18). Moving to the API layer.
> *(Read `app/api.py` in the same message)*

Keep notes to one or two sentences: what changed, what is next. Save the full account for the
final report.

## 5. Stops we do want

These are real blockers. Stop for them:

- **Missing credentials or secrets**: an API key, token, or login that is not in the environment
  and that you must not invent.
- **An ambiguous requirement that changes the design**: the options lead to different
  architectures and the remaining work depends on the choice.
- **Protected resources**: a branch, file, directory, or environment you are denied, or a tool call
  the harness refused. Do not route around a denial.
- **Destructive or irreversible actions**: dropping or migrating data in place, force-pushing,
  deleting files outside the task, sending email or messages, deploying to production, spending
  money. These need a yes even when everything else says keep going.

Write each one on its own line in this form: `BLOCKED: <what> <what you need from me>`. Use
`NEEDS-YOU:` for a decision rather than a missing resource.

```
BLOCKED: deploy to staging. Need STAGING_TOKEN exported, it is not set in this environment.
BLOCKED: migration 0042 drops legacy_orders (1.2M rows). Need a yes before I run it.
NEEDS-YOU: rate limits per user or per API key. Everything else is done and tested.
```

Before you write one, finish everything that does not depend on it. A blocker on item 4 does not
stop items 5 and 6.

The hook recognizes these tokens and lets the stop through. That makes a fabricated blocker the
one way around it, so never write one to escape. These are not blockers:

- "I need your confirmation to continue" for work the user already asked for.
- A failing test you have not debugged yet.
- A missing package you can install with the tools you have.
- Uncertainty about style or naming that is cheap to change later.

## 6. When the hook blocks you

You will receive one of two messages. For open checklist items:

```
Open items: test in tests/test_api.py; CHANGELOG.md line under Unreleased. Continue with them.
If one is blocked, say what is blocking it on a line that starts with BLOCKED:.
```

Or, when there is no checklist, a note that names the early-stop pattern your last message
matched and quotes the phrase.

What to do:

- **Do not re-summarize and do not apologize.** Your next message starts with a tool call for the
  first open item.
- **Item already done?** You forgot to mark it. Mark it completed and move on.
- **Item no longer needed?** Delete it and say why in one line.
- **Item blocked?** Write the `BLOCKED:` line, after doing everything else you can.
- **Pattern note on a finished task**, for example you ended with an offer of optional extra
  work? End with the final report and no offer.

The hook allows at most three automatic continuations per user turn (`CLIFFHANGER_MAX`). If you
reach that, the run is stuck. Say what is stuck in a `BLOCKED:` line instead of another summary.

## 7. Final report

End with one line per checklist item, done or blocked, then one line saying what the user should
verify. Nothing after it.

```
- [x] GET /health in app/api.py, returns {"status": "ok", "version": "0.4.1"}
- [x] tests/test_api.py::test_health, full suite 31 passed
- [x] docs/api.md entry under Endpoints
- [ ] CHANGELOG.md line
BLOCKED: CHANGELOG.md is read-only in this sandbox. Need write access, or add "Added GET /health" yourself.
Verify: curl -s localhost:8000/health
```

No "let me know if you'd like...", no menu of follow-ups. If you noticed something worth doing
beyond the task, give it one line starting with `Out of scope:` and do not offer to do it.
