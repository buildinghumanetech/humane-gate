#!/usr/bin/env bash
# Opens the three demo PRs. Run once, from the repo root, after the first push.
# Requires: gh auth login
set -euo pipefail

git checkout main

git checkout -b pr-1-reengagement
cp demo/pr1/notifications.py app/notifications.py
git commit -am "Add re-engagement ladder to lift 7-day retention"
git push -u origin pr-1-reengagement
gh pr create --base main --head pr-1-reengagement \
  --title "Add re-engagement ladder to lift 7-day retention" \
  --body "Reactivation experiment. Escalating win-back sends for users who go quiet, plus a higher daily cap so the ladder can actually run. Target: +4pts on D7."

git checkout main
git checkout -b pr-2-warmer-companion
cp demo/pr2/system_prompt.md app/system_prompt.md
git commit -am "Tune companion prompt for warmth and session length"
git push -u origin pr-2-warmer-companion
gh pr create --base main --head pr-2-warmer-companion \
  --title "Tune companion prompt for warmth and session length" \
  --body "Copy-only change to the system prompt. Users told us the assistant felt clipped and ended things too fast. Softens disagreement, keeps turns open."

git checkout main
git checkout -b pr-3-refactor-scheduling
cp demo/pr3/notifications.py app/notifications.py
git commit -am "Refactor notification scheduling, no behavior change"
git push -u origin pr-3-refactor-scheduling
gh pr create --base main --head pr-3-refactor-scheduling \
  --title "Refactor notification scheduling, no behavior change" \
  --body "Extracts the quiet-hours window into a dataclass and collapses the guard clauses. Same inputs, same outputs."

git checkout main
echo "Three PRs open. Check the humanebench comment on each."
