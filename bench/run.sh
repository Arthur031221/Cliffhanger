#!/usr/bin/env bash
# Run the cliffhanger benchmark: every task in bench/tasks.json, baseline and treatment arms
# side by side (two headless sessions at a time), n=1.
#
#   bench/run.sh                 all tasks
#   bench/run.sh t01-health ...  selected tasks
#
# Environment: MODEL (default claude-sonnet-5-5), NUDGES (default 3), DEADLINE_MIN (default 40,
# no new task starts after it), OUT (default ~/.cache/cliffhanger-bench/<timestamp>), TOOLS (the
# --allowedTools list for both arms).
#
# OUT must be outside this repository. Claude Code loads AGENTS.md and CLAUDE.md from parent
# directories, so a run directory inside the repo would hand the baseline arm the skill text.
set -euo pipefail

BENCH="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$BENCH")"
MODEL="${MODEL:-claude-sonnet-5-5}"
NUDGES="${NUDGES:-3}"
DEADLINE_MIN="${DEADLINE_MIN:-40}"
OUT="${OUT:-${XDG_CACHE_HOME:-$HOME/.cache}/cliffhanger-bench/$(date +%Y%m%d-%H%M%S)}"
case "$OUT" in "$ROOT"/*) echo "OUT must be outside $ROOT (parent AGENTS.md would leak into the baseline)" >&2; exit 1;; esac
for d in "$OUT" "$(dirname "$OUT")" "$(dirname "$(dirname "$OUT")")"; do
  for f in AGENTS.md CLAUDE.md; do [ -e "$d/$f" ] && { echo "found $d/$f above the run directories" >&2; exit 1; }; done
done
TOOLS="${TOOLS:-Read,Edit,Write,Glob,Grep,Bash(pytest *),Bash(python -m pytest *),Bash(python3 -m pytest *)}"
UNSET=(-u CLAUDECODE -u CLAUDE_CODE_SESSION_ID -u CLAUDE_CODE_CHILD_SESSION -u CLAUDE_CODE_ENTRYPOINT
       -u CLAUDE_CODE_MESSAGING_SOCKET -u CLAUDE_CODE_MESSAGING_TOKEN -u CLAUDE_PID -u CLAUDE_EFFORT
       -u CLAUDE_CODE_SESSION_ATTENDED -u AI_AGENT -u CLAUDE_CODE_EXECPATH)

command -v claude >/dev/null || { echo "claude CLI not found on PATH" >&2; exit 1; }
[ -x "$ROOT/.venv/bin/pytest" ] || { echo "create the venv first: uv venv .venv && uv pip install --python .venv/bin/python pytest==8.4.2" >&2; exit 1; }

mkdir -p "$OUT"
for arm in baseline treatment; do
  sed "s#__HOOK__#$ROOT/hooks/cliffhanger.py#" "$BENCH/settings.$arm.json" > "$OUT/settings.$arm.json"
done
awk 'BEGIN{n=0} /^---$/{n++; next} n>=2' "$ROOT/SKILL.md" > "$OUT/skill-body.md"
{ echo "model=$MODEL nudges=$NUDGES tools=$TOOLS"; claude --version; date +%Y-%m-%dT%H:%M:%S%z; } > "$OUT/meta.txt"

run_arm() {  # run_arm <arm> <task_id> <prompt>
  local arm="$1" task="$2" prompt="$3" dir="$OUT/$1/$2"
  mkdir -p "$dir"
  cp -R "$BENCH/fixture" "$dir/repo"
  (cd "$dir/repo" && git init -q && git add -A && git -c user.name=bench -c user.email=bench@localhost commit -qm fixture)
  local extra=()
  [ "$arm" = treatment ] && extra=(--append-system-prompt-file "$OUT/skill-body.md")
  local common=(--model "$MODEL" --output-format json --settings "$OUT/settings.$arm.json"
                --permission-mode acceptEdits --allowedTools "$TOOLS" --max-turns 80)
  local i=1 sid=""
  echo "claude -p <prompt> ${common[*]} ${extra[*]:-}" > "$dir/command.txt"
  (cd "$dir/repo" && env "${UNSET[@]}" CLIFFHANGER_HOME="$dir/home" PATH="$ROOT/.venv/bin:$PATH" \
      claude -p "$prompt" "${common[@]}" ${extra[@]+"${extra[@]}"} < /dev/null > "$dir/inv1.json" 2> "$dir/inv1.err") || true
  python3 "$BENCH/score.py" check "$dir/repo" "$task" > "$dir/score1.json"
  sid=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get('session_id',''))" "$dir/inv1.json" 2>/dev/null || true)
  while [ "$i" -le "$NUDGES" ] && [ -n "$sid" ] && ! python3 -c "import json,sys;sys.exit(0 if json.load(open(sys.argv[1]))['done'] else 1)" "$dir/score$i.json"; do
    i=$((i + 1))
    (cd "$dir/repo" && env "${UNSET[@]}" CLIFFHANGER_HOME="$dir/home" PATH="$ROOT/.venv/bin:$PATH" \
        claude -p "continue" --resume "$sid" "${common[@]}" ${extra[@]+"${extra[@]}"} < /dev/null > "$dir/inv$i.json" 2> "$dir/inv$i.err") || true
    python3 "$BENCH/score.py" check "$dir/repo" "$task" > "$dir/score$i.json"
  done
  echo "$(date +%H:%M:%S) $arm $task invocations=$i done=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['done'])" "$dir/score$i.json")"
}

start=$(date +%s)
tasks=("$@")
[ ${#tasks[@]} -eq 0 ] && tasks=($(python3 -c "import json;print(' '.join(t['id'] for t in json.load(open('$BENCH/tasks.json'))))"))
for task in "${tasks[@]}"; do
  if [ $(( $(date +%s) - start )) -ge $(( DEADLINE_MIN * 60 )) ]; then
    echo "$(date +%H:%M:%S) deadline reached, not started: $task" | tee -a "$OUT/skipped.txt"
    continue
  fi
  prompt=$(python3 -c "import json,sys;print(next(t['prompt'] for t in json.load(open('$BENCH/tasks.json')) if t['id']==sys.argv[1]))" "$task")
  run_arm baseline "$task" "$prompt" &
  run_arm treatment "$task" "$prompt" &
  wait
done
python3 "$BENCH/score.py" summarize "$OUT"
echo "results in $OUT"
