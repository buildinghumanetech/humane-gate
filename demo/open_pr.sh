#!/usr/bin/env bash
# Open one demo pull request.   ./demo/open_pr.sh 5
#
#   1  re-engagement ladder        front end + copy      expect: flags
#   2  companion prompt tuned      prompt only           expect: flags
#   3  scheduling refactor         no behavior change    expect: clean
#   5  soft-delete retention       backend only          expect: flags
#   6  queue-level consent         backend only          expect: clean + commends
#   7  daily cap 2 to 3            one constant          expect: honestly ambiguous
#   8  memory with disclosure      prompt + copy         expect: clean + commends
set -euo pipefail
cd "$(dirname "$0")/.."
n="${1:?usage: ./demo/open_pr.sh <1|2|3|5|6|7|8>}"

srcs=(); dsts=()
case "$n" in
  1) branch=pr-1-reengagement;        srcs=(demo/pr1/notifications.py); dsts=(app/notifications.py)
     title="Add re-engagement ladder to lift 7-day retention"
     body="Reactivation experiment. Escalating win-back sends for users who go quiet, plus a higher daily cap so the ladder can run. Target: +4pts on D7." ;;
  2) branch=pr-2-warmer-companion;    srcs=(demo/pr2/system_prompt.md); dsts=(app/system_prompt.md)
     title="Tune companion prompt for warmth and session length"
     body="Copy-only change to the system prompt. Users told us the assistant felt clipped and ended things too fast. Softens disagreement, keeps turns open." ;;
  3) branch=pr-3-refactor-scheduling; srcs=(demo/pr3/notifications.py); dsts=(app/notifications.py)
     title="Refactor notification scheduling, no behavior change"
     body="Extracts the quiet-hours window into a dataclass and collapses the guard clauses. Same inputs, same outputs." ;;
  5) branch=pr-5-soft-delete;         srcs=(demo/pr5/storage.py); dsts=(app/storage.py)
     title="Switch account deletion to soft delete for cohort continuity"
     body="Retention reporting keeps breaking when deleted accounts vanish mid-cohort, and win-back can't restore anyone. Flags the rows instead of purging them. No UI change." ;;
  6) branch=pr-6-queue-consent;       srcs=(demo/pr6/notifications.py); dsts=(app/notifications.py)
     title="Enforce mute and quiet hours at the queue, require opt-in for reactivation"
     body="Mute was only checked in the send path, so retries and background jobs could get around it. Moves the check to the queue, requires explicit opt-in before any reactivation send, and adds a one-tap unsubscribe that needs no login." ;;
  7) branch=pr-7-cap-three;           srcs=(demo/pr7/notifications.py); dsts=(app/notifications.py)
     title="Raise daily notification cap from 2 to 3"
     body="Product wants one more slot for the daily digest. One constant. Mute, quiet hours and everything else unchanged." ;;
  8) branch=pr-8-memory-disclosed;    srcs=(demo/pr8/system_prompt.md demo/pr8/onboarding.md)
                                      dsts=(app/system_prompt.md app/copy/onboarding.md)
     title="Ship cross-session memory with disclosure and user controls"
     body="The assistant now remembers past sessions. Onboarding says so, Settings lets people read, correct, export, turn off or delete what is stored, and the prompt attributes memories to the user rather than to the assistant." ;;
  *) echo "pick 1, 2, 3, 5, 6, 7 or 8"; exit 1 ;;
esac

# Re-runnable: rebuild the branch from current main so a reopened PR gets a
# fresh head sha and therefore a clean check-run history.
git checkout main -q
git branch -D "$branch" -q 2>/dev/null || true
git checkout -b "$branch" -q
for i in "${!srcs[@]}"; do cp "${srcs[$i]}" "${dsts[$i]}"; done
git commit -qam "$title"
git push -qfu origin "$branch"
gh pr create --base main --head "$branch" --title "$title" --body "$body"
git checkout main -q
