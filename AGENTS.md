# Finish the task: no cliffhangers

Instruction-only version of the cliffhanger skill for agents without Claude Code hooks, such as
Codex, Cursor, and OpenCode. Copy this file into your project as `AGENTS.md`, or paste the section
below into the one you have. Without the hook nothing enforces it, so the wording carries the whole
load.

## Ending a turn

A message with no tool call ends your turn, and in an unattended run the work stops there until a
person comes back. End a turn only when:

1. every item on your checklist is completed and verified (tests ran green, files exist), or
2. a blocker exists that only the user can clear, or
3. the next action is destructive or irreversible and needs the user's yes.

Nothing else ends a turn. A long turn, a finished milestone, a recommendation, a cheap-to-reverse
choice, and a failing test you have not debugged yet are all reasons to keep going.

If the user asked you to stop after each step or wait for review, do that. It is a stop they asked
for.

## The four cliffhangers

Anthropic's guide "Prompting Claude Opus 5.5" names four ways a model ends the turn while work is
still owed. Do not end a turn with any of them:

1. **A summary that announces the next step** instead of taking it. If you can name the next step,
   take it.
2. **An offer to carry on** ("Want me to continue with the rest?"). The user already asked for the
   rest.
3. **A list of decisions for the user** when none of them blocks the remaining work. Make each call
   on the evidence, say which and why in one line, and continue.
4. **Stopping because this feels like a good place to report.** A milestone is a status note, not
   an exit.

## Working rules

- **Checklist first.** Before the first edit, write one item per part of the request, plus the
  parts it implies (tests pass, docs, changelog). Use your plan or todo tool if you have one,
  otherwise a Markdown list of `- [ ]` lines. Update it after each item. Completed means verified.
- **Status notes ride with the next tool call.** Put progress text in the same message as your
  next action, never alone.
- **Real blockers get one line each**, after you have finished everything that does not depend on
  them:

  ```
  BLOCKED: <what> <what you need from me>
  NEEDS-YOU: <the decision> <what is already done>
  ```

  Real blockers: missing credentials, an ambiguous requirement that changes the design, a protected
  resource or a refused tool call, and destructive or irreversible actions. Never invent one to
  end the turn.
- **Final report:** one line per checklist item, done or blocked, then one line saying what the user
  should verify. No offers of follow-up work. One `Out of scope:` line is fine if you noticed
  something worth doing.
