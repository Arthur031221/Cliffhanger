# Contributing

## Setup

```
uv venv .venv && uv pip install --python .venv/bin/python pytest==8.4.2
.venv/bin/python -m pytest
uvx ruff@0.14.0 check .
```

The hook and the CLI use the Python standard library only and must keep working on Python 3.8.

## Changing the detector

Most contributions will be new phrases for the regex bank in `hooks/cliffhanger.py`. Each one
needs two tests in `tests/test_hook.py`:

1. a real last message it must block, pasted from a transcript (trim it, keep the wording), and
2. a real final report it must still allow.

A phrase that blocks finished work costs the user a wasted turn every time it fires. When in doubt,
leave it out. The checklist path is the primary signal and the regex bank is the fallback.

Keep `hooks/cliffhanger.py` under 200 lines. It runs on every stop of every session.

## Benchmark

`bench/run.sh` spends real money on API calls and takes about 40 minutes. Do not add it to CI. If
you change the detector or the skill and rerun it, commit the new `bench/results.md` section with
the command line, Claude Code version, model, and date, and keep the old section.

## Commits

One logical change per commit, imperative subject line.
