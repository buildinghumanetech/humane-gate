#!/usr/bin/env bash
# Open a demo proposal as an issue and let the check review it.
#
#   ./demo/open_proposal.sh streaks
#
# Product people arrive by a different door than engineers do. This is that door.
set -euo pipefail
cd "$(dirname "$0")/.."
name="${1:-streaks}"
file="demo/proposals/${name}-prd.md"
[ -f "$file" ] || { echo "no such proposal: $file"; exit 1; }

title=$(head -1 "$file" | sed 's/^# *//')
gh label create humane-review \
  --description "Ask HumaneBench to review this proposal" \
  --color 0e8a16 2>/dev/null || true
url=$(gh issue create --title "$title" --body-file "$file" --label humane-review)
echo "$url"
echo "the check runs on the label; give it a minute"
