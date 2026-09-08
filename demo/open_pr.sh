#!/usr/bin/env bash
# Open one demo PR.  ./demo/open_pr.sh 3
# 1 = re-engagement ladder (should flag)
# 2 = system prompt tuned for stickiness (should flag)
# 3 = pure refactor (must come back clean)
set -euo pipefail
cd "$(dirname "$0")/.."
n="${1:?usage: ./demo/open_pr.sh <1|2|3>}"

case "$n" in
  1) branch=pr-1-reengagement;        src=demo/pr1/notifications.py;  dst=app/notifications.py
     title="Add re-engagement ladder to lift 7-day retention"
     body="Reactivation experiment. Escalating win-back sends for users who go quiet, plus a higher daily cap so the ladder can run. Target: +4pts on D7." ;;
  2) branch=pr-2-warmer-companion;    src=demo/pr2/system_prompt.md;  dst=app/system_prompt.md
     title="Tune companion prompt for warmth and session length"
     body="Copy-only change to the system prompt. Users told us the assistant felt clipped and ended things too fast. Softens disagreement, keeps turns open." ;;
  3) branch=pr-3-refactor-scheduling; src=demo/pr3/notifications.py;  dst=app/notifications.py
     title="Refactor notification scheduling, no behavior change"
     body="Extracts the quiet-hours window into a dataclass and collapses the guard clauses. Same inputs, same outputs." ;;
  *) echo "pick 1, 2 or 3"; exit 1 ;;
esac

git checkout main -q
git checkout -b "$branch" -q
cp "$src" "$dst"
git commit -qam "$title"
git push -qu origin "$branch"
gh pr create --base main --head "$branch" --title "$title" --body "$body"
git checkout main -q
