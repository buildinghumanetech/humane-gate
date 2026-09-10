# Humane Gate

A HumaneBench check that runs on every pull request, scores the diff against
**HumaneBench rubric v3.0**, and **blocks nothing**.

The rubric is not reimplemented here. `rubrics/rubric_v3.md` is vendored byte-for-byte
from [buildinghumanetech/humanebench](https://github.com/buildinghumanetech/humanebench/blob/main/rubrics/rubric_v3.md)
and loaded as the first half of the judge's system prompt. The second half only
explains how to apply a response rubric to a code diff. Every deviation is
enumerated in [`RUBRIC_DELTAS.md`](RUBRIC_DELTAS.md).

Advisory, not a gate. A team can see what it would have caught, on their real
pull requests, for thirty days, before deciding whether it should ever have teeth.

## What it does

On each PR, the check posts **one verdict** and a `neutral` check run named
`humanebench / advisory`.

| | |
|---|---|
| 🟢 `clear` | Nothing to raise. Most pull requests. |
| 🟡 `review` | Something worth a look. Nobody is blocked. |
| 🟠 `discuss` | A floor concern. Worth a conversation before it ships. |
| 🔵 needs context | The judge cannot tell from the diff alone, so it asks. |

There is no red. Red means "blocked" everywhere else in CI, this check blocks
nothing, and an engineer who sees red stops reading. Findings sit folded behind
the verdict, because the first line is the one that gets read.

**Needs context is the important one.** A diff does not contain the conversation
it sits in, the policy that governs it, or the screen the user sees. When a
verdict depends on something the diff cannot show, the check asks a question
instead of guessing. A wrong finding costs you the engineer; a question costs
them ten seconds. Re-running edits the same comment rather than
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
| 9 | The policy file itself is loosened for Q4 | `humane-policy.toml` | flags |

## Values as code

`humane-policy.toml` is where an organization writes its own numbers: the
notification ceiling, whether a mute is absolute, how long deleted data survives,
whether minors can be bucketed into engagement arms. The rubric says what humane
means. The policy says what the threshold is.

The judge reads it as the team's own stated values and scores against **their**
number rather than substituting one. That is what makes an otherwise unanswerable
change like a daily cap moving from 2 to 3 resolvable: inside the policy, not a
finding; past it, a finding that cites their own file.

A diff that edits the policy is in scope, and it is the most consequential kind
of change in the repo. It moves what the product may do to people for every
future pull request at once. PR 9 is that change.

3, 6, 8 and 9 are the important ones. A check that only ever says no gets switched
off, and a check that fires on a refactor gets switched off faster.

## Disagreeing with it

Every finding carries a short id. Anyone with write access on the repo can close
one by replying on the pull request:

```
/humane accept BTH-50f8c5 crisis-flagged users are excluded upstream in the router
```

The check re-runs on the reply and moves that finding into **Accepted, on the
record**: your name, your reason in your own words, the timestamp, and the commit
it covers. It stops driving the verdict.

Three things about that, in order of how much they matter:

- **It is scoped to a commit.** Push after signing and the acceptance no longer
  covers what is in the branch, and the finding reopens. An acceptance is of one
  risk in one diff, not a standing waiver.
- **Standing is checked.** `OWNER`, `MEMBER` or `COLLABORATOR` only. A comment
  from a fork or a bot is ignored and the check says so in the log.
- **The record is the GitHub comment**, not a ledger this tool writes. GitHub
  already stores the author, the timestamp and the full edit history, and will
  not let one account post as another. A second ledger next to that one would be
  worse in every way that matters to somebody auditing it later.

Some findings arrive already conditional, as **"-1.0 unless X"**, with the exact
reply that would close them. That is the check asking a question, because CI
cannot hold a conversation and a reply is the only kind it can receive.

## Reviewing a proposal instead of a diff

Product decisions are made in documents, weeks before they are code. Same rubric,
same floor, same policy documents:

```bash
# a PRD pasted into a GitHub issue
gh issue create --title "PRD: daily streaks" --body-file prd.md --label humane-review

# a spec that lives in the repo
gh workflow run humanebench-doc.yml -f path=docs/specs/streaks.md

# anything you can copy out of Linear or Notion
pbpaste | DRY_RUN=1 python humanebench/judge.py --document
```

One rule differs. In a diff, a missing guard is usually a guard you cannot see,
so absence proves nothing. In a proposal, a missing consideration is usually a
missing consideration, so absence is evidence.

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
| `humane-policy.toml` | This organization's own thresholds. Values as code. |
| `rubrics/rubric_v3.md` | HumaneBench rubric v3.0, byte-identical to upstream. Never hand-edit. |
| `rubrics/VERSION` | Which upstream commit is pinned, and its sha256. |
| `scripts/sync_rubric.sh` | Pull a fresh rubric. Refuses an empty or unrecognizable file. |
| `RUBRIC_DELTAS.md` | Every way the PR check differs from v3, and why. |
| `humanebench/prompt.md` | The adaptation layer: response rubric to code diff. Anti-noise rules live here. |
| `humanebench/prompt_document.md` | The same, for a PRD or ticket instead of a diff. |
| `humanebench/judge.py` | Read, call, filter, post. The verdict, the floor and the acceptances are computed here, not by the model. |
| `docs/` | Policy documents the check reads before it judges. |
| `.github/workflows/humanebench.yml` | `on: pull_request` and `on: issue_comment`, plus `workflow_dispatch` so you can re-run it live. |
| `.github/workflows/humanebench-doc.yml` | Reviews an issue labelled `humane-review`, or a document path. |
| `app/` | A small companion app to have PRs against. |
| `demo/` | Nine demo pull requests and a demo PRD. |

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
