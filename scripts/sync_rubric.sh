#!/usr/bin/env bash
# Pull the current HumaneBench rubric from the benchmark repo into rubrics/.
#
# The vendored file is what actually runs. This script replaces it and records
# provenance in rubrics/VERSION. It never runs during a PR check: the rubric a
# verdict was produced under must be pinned and auditable, not fetched live.
#
#   ./scripts/sync_rubric.sh            # sync, report whether anything changed
#   ./scripts/sync_rubric.sh --check    # exit 1 if drifted, change nothing
set -euo pipefail

UPSTREAM_REPO="buildinghumanetech/humanebench"
UPSTREAM_PATH="rubrics/rubric_v3.md"
LOCAL="rubrics/rubric_v3.md"
RAW="https://raw.githubusercontent.com/${UPSTREAM_REPO}/main/${UPSTREAM_PATH}"

cd "$(dirname "$0")/.."
mkdir -p rubrics
tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

curl -fsSL "$RAW" -o "$tmp"
[ -s "$tmp" ] || { echo "sync_rubric: upstream returned an empty file, refusing"; exit 1; }
grep -q "Principle-by-Principle Rubric" "$tmp" || {
  echo "sync_rubric: fetched file does not look like the rubric, refusing"; exit 1; }

if [ -f "$LOCAL" ] && cmp -s "$tmp" "$LOCAL"; then
  echo "sync_rubric: up to date"
  exit 0
fi

if [ "${1:-}" = "--check" ]; then
  echo "sync_rubric: DRIFT. Local rubric differs from ${UPSTREAM_REPO}."
  diff -u "$LOCAL" "$tmp" || true
  exit 1
fi

# Provenance. The short sha goes in every PR comment footer, so any finding can
# be traced back to the exact rubric text that produced it.
sha="$(curl -fsSL \
  "https://api.github.com/repos/${UPSTREAM_REPO}/commits?path=${UPSTREAM_PATH}&per_page=1" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["sha"])' 2>/dev/null || echo unknown)"

cp "$tmp" "$LOCAL"
cat > rubrics/VERSION <<META
source:      ${UPSTREAM_REPO}/${UPSTREAM_PATH}
commit:      ${sha}
sha256:      $(shasum -a 256 "$LOCAL" | cut -d' ' -f1)
fetched_utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)

This file is byte-identical to upstream. Do not hand-edit it. Deviations the
PR check makes are in RUBRIC_DELTAS.md, never in the rubric itself.
META

echo "sync_rubric: updated to ${sha:0:7}"
