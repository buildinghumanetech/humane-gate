# Humane Gate, shadow mode

A HumaneBench check that runs on every pull request, scores the diff against
**HumaneBench rubric v3.0**, and **blocks nothing**.

The rubric is not reimplemented here. `rubrics/rubric_v3.md` is vendored byte-for-byte
from [buildinghumanetech/humanebench](https://github.com/buildinghumanetech/humanebench/blob/main/rubrics/rubric_v3.md)
and loaded as the first half of the judge's system prompt. The second half only
explains how to apply a response rubric to a code diff. Every deviation is
enumerated in [`RUBRIC_DELTAS.md`](RUBRIC_DELTAS.md).

The point of shadow mode: a team can see what the gate would catch, on their real
PRs, for thirty days, before deciding whether it should ever gate anything.

## What it does

On each PR, the check posts one comment with any findings, and a `neutral` check
run named `humanebench / shadow`. Re-running edits the same comment rather than
stacking new ones.

A finding has to survive three filters before anyone sees it:

- the diff has to change the range of experiences a person can have (refactors,
  tests and deps return clean)
- the finding has to name the downstream consequence for a person, and cite the
  v3 tier its rationale relies on
- the quoted evidence has to actually appear in the diff, checked in code
- the judge has to quote the exact changed line as evidence
- the judge has to mark the finding `medium` or `high` confidence

Anything else is dropped by the runner, not by the model.

## Setup

1. New public repo, push this.
2. **`./scripts/sync_rubric.sh`** — the checked-in rubric is a hand-transcription
   until you run this once. It replaces it with the real bytes and pins the commit.
3. `gh secret set ANTHROPIC_API_KEY`
4. `./demo/open_pr.sh 1` and so on, one at a time

## Keeping the rubric current

The rubric is **pinned**, not fetched at run time. A verdict has to be traceable to
the exact rubric text that produced it, and a check that reaches the network on
every PR is a check that fails on every network blip.

Drift is handled as a pull request instead:

| | |
|---|---|
| `./scripts/sync_rubric.sh` | Sync now, record commit + sha256 in `rubrics/VERSION`. |
| `./scripts/sync_rubric.sh --check` | Exit 1 if drifted. Changes nothing. |
| `.github/workflows/rubric-sync.yml` | Mondays 14:00 UTC. Opens a PR when upstream moves. |

Every PR comment footer carries the pinned short sha. Merging a rubric-sync PR
changes what every future verdict means, so re-run the three demo PRs before
merging one. The clean PR has to stay clean.

Seven demo pull requests, `./demo/open_pr.sh <n>`:

| n | Change | Layer | Expect |
|---|---|---|---|
| 1 | Re-engagement ladder | copy + scheduling | flags |
| 2 | Companion prompt tuned for stickiness | prompt | flags |
| 3 | Scheduling refactor | none | clean |
| 5 | Account deletion becomes a flag | backend, no UI | flags |
| 6 | Mute enforced at the queue, opt-in required | backend, no UI | clean, commended |
| 7 | Daily cap 2 to 3 | one constant | honestly ambiguous |
| 8 | Memory shipped with disclosure and controls | prompt + copy | clean, commended |

3, 6 and 8 are the important ones. A check that only ever says no gets switched
off, and a check that fires on a refactor gets switched off faster.

## Local dry run, no GitHub

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...
export DRY_RUN=1
export BASE_SHA=$(git rev-parse main) HEAD_SHA=$(git rev-parse HEAD)
python humanebench/judge.py
```

## Files

| Path | What |
|---|---|
| `rubrics/rubric_v3.md` | HumaneBench rubric v3.0, byte-identical to upstream. Never hand-edit. |
| `rubrics/VERSION` | Which upstream commit is pinned, and its sha256. |
| `scripts/sync_rubric.sh` | Pull a fresh rubric. Refuses an empty or unrecognizable file. |
| `RUBRIC_DELTAS.md` | Every way the PR check differs from v3, and why. |
| `humanebench/prompt.md` | The adaptation layer: response rubric to code diff. Anti-noise rules live here. |
| `humanebench/judge.py` | Diff, call, filter, post. ~170 lines. |
| `.github/workflows/humanebench.yml` | `on: pull_request`, plus `workflow_dispatch` so you can re-run it live. |
| `app/` | A small companion app to have PRs against. |
| `demo/` | The three demo PRs. |

## Threat model

The gate runs from the default branch. The pull request is fetched as loose git
objects, never checked out, never built, never executed; only its diff text is
read. So a PR cannot edit `humanebench/prompt.md`, `rubrics/rubric_v3.md` or
`judge.py` and then be scored by its own edits.

**Not yet closed:** for same-repository pull requests, GitHub runs the workflow
file from the PR itself, so a PR can still edit `.github/workflows/humanebench.yml`.
Closing that needs GitHub-side controls, a branch ruleset with a required
workflow, not anything this repo can do to itself. Any real deployment should
turn those on. Credit to the Sparkle implementation for the two-checkout design.

## Notes

- Single judge, and **verdicts are not reproducible**: the current Messages API
  exposes no temperature or top_p, so a re-run on the same diff can differ. See
  "Known limitations" in `RUBRIC_DELTAS.md` for what the check does about it and
  what would actually fix it.
- Set `HUMANEBENCH_MODEL` to whichever model you have access to.
- Secrets are not available to `pull_request` runs from forks. Fine for a demo
  repo you own; a real deployment uses `pull_request_target` with a pinned
  checkout, or a GitHub App.
- The check run is hardcoded to `conclusion: neutral`. Making it gate is a
  one-line change, and that line is the thirty-day decision.
