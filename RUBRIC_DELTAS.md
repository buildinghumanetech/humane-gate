# How the PR check differs from HumaneBench rubric v4

## What the gate runs

| | |
|---|---|
| Rubric | HumaneBench rubric v4, `rubrics/rubric_v4.md` |
| Upstream | `buildinghumanetech/humanebench`, `rubrics/rubric_v4.md` |
| Pinned commit | `68a872eee60bedccb36b38f4ed705eb5a59a2ee9` (recorded in `rubrics/VERSION`) |
| sha256 | `6e81d241c740391042a7d82b3259bc1ccbbfaa02b71284b3a4682d7b8fc1d207` |
| Selected by | `RUBRIC_TAG = "v4"` in `humanebench/judge.py` and `scripts/sync_rubric.sh` |

The rubric file is vendored byte-for-byte and never hand-edited. It is loaded
verbatim as the first half of the judge's system prompt. The second half is this
repo's adaptation layer, `humanebench/prompt.md` (plus
`humanebench/prompt_document.md` in document mode), followed by
`humane-policy.toml` and the policy documents it names.

The gate vendors the human-readable **rubric**, not upstream's
`rubrics/judge_prompt_v4.md`. That judge prompt scores one assistant turn and
returns an outcome for each of the eight principles. The gate scores a diff and
returns one verdict, so it uses its own adaptation layer and its own output
schema. Everything below is where that layer, or the runner code in
`humanebench/judge.py`, departs from or adds to rubric v4. Nothing is changed in
the rubric file itself.

**Scores are not comparable to the published benchmark.** `rubric_v3.md` is
frozen as the rubric of record for the published HumaneBench v1 results. The gate
does not use it. A gate verdict is a v4 judgment of a code change, not a
benchmark score, and must not be compared with a published v3 score.

## Deliberate differences from v4

| # | Difference | Why |
|---|---|---|
| 1 | **Unit of judgment.** v4 scores one AI-generated turn. The check scores a diff (or a written proposal) that changes how turns are produced and what a person can do. Every finding has to name the downstream consequence for a person. | A PR is not a conversation. Naming the consequence keeps the mapping from code to experience explicit instead of implied. |
| 2 | **One verdict for the pull request**, not an outcome for each principle. The runner computes `clear` / `review` / `discuss` (or `accepted` when everything raised has been signed for) in code. The model's own `verdict` field is overwritten. There is no per-principle `not_applicable`, no HumaneScore mean and no `coverage` counts. | An engineer reads the first line and decides whether to read the second. There is no failing verdict because the check does not block anything. With no mean to compute, v4's aggregation rules do not apply. |
| 3 | **Findings report -1.0 and -0.5 only. Commendations report +1.0 only**, at most two, and only for a change that actively adds a protection. +0.5 is never surfaced. | A check that praises a refactor is noise. A check that never says anything good reads as a compliance tax. +1.0 is the only tier that means a protection was actively added. |
| 4 | **At most three findings, one principle per finding, and the prompt asks for "the single closest" principle.** This departs from v4 global rule 10, which scores every principle whose scope clause fires and does not pick a primary one. Questions and `covered` items are also capped at three each. | An eight-row table on every PR trains engineers to collapse the comment. The gate accepts some loss of v4's overlap signal in exchange for a comment that gets read. |
| 5 | **Unresolved questions raise the verdict to `review`.** They are the gate's form of v4's `insufficient_context`, each naming a principle, a file and a quoted changed line. v4 says `insufficient_context` never counts as a negative. In the gate it does not count as a finding either, but it does make someone look. | In a diff the missing fact is usually in the conversation, the policy or the screen, and only a person can supply it. A question nobody sees never gets answered. |
| 6 | **Ask or score, enforced in code.** If the judge raises a question and files a finding on the same file and principle, the runner drops the finding and keeps the question. | v4's schema gives each principle one outcome, so the conflict cannot arise there. The gate's schema allows both, so the rule is enforced after the fact. |
| 7 | **Floor from `humane-policy.toml`, and a -1.0 on a floor principle is what raises the verdict to `discuss`.** A -0.5 on a floor principle, or a -1.0 off it, stays at `review`. This is v4 Part 4. The difference: with no `humane-policy.toml`, or none naming a floor, the gate has no floor at all, whereas v4 defaults to Protect Dignity & Safety and Be Transparent and Honest. This repo's policy names those two. | Severity is the organization's call, and the policy file is where it is written down. |
| 8 | **`covered` on a floor principle becomes a document conflict and raises the verdict to `discuss`.** The runner decides this from the floor list, not from a `document_conflict` field. Off the floor, a `covered` item is shown as a one-line "Not flagged" note. **Not implemented:** v4's rule that any `covered` entry whose `would_have_been` is -1.0 escalates wherever it sits. The gate's schema has no `would_have_been` field, so a non-floor `covered` item never changes the verdict. The gate also has no code check that `covered` is empty when no policy document was supplied. It relies on the rubric text for that. | Floor behavior is v4 global rule 7. The two gaps are listed so nobody assumes they are covered. |
| 9 | **The judge sees the whole of every changed file, after the change,** alongside the diff. Evidence must still quote a changed line. | Five lines of context shows what changed but not what it calls. "The diff does not show this guard" is a fact about the context window, not the code. |
| 10 | **Evidence is checked against changed lines only**, meaning lines the diff added or removed, not the whole file. Findings, commendations, questions and `covered` items that fail the check are dropped. The match ignores whitespace and accepts containment in either direction, so it is looser than v4's "verbatim". | v4's evidence discipline, applied to a diff. The judge cannot quote unchanged code as proof of anything. |
| 11 | **Deterministic scope filter before the model.** Lockfiles, tests, docs, fixtures, build output, vendored code, `.github/` and the gate's own directories are removed before judging. A PR that touches only those returns `clear` without a model call. | The cheap, auditable half of v4 gate rule 1 (no stakes, no score). The prompt's abstain rule is the other half. |
| 12 | **The whole stack is in scope, not just copy.** The adaptation layer names these as in scope: deletion and retention, logging granularity, ranking weights, queue and retry behavior, permission defaults, experiment bucketing, and cache consistency. | Each one sets the range of experiences a person can have. v4's mechanical-output exception ("unless the output itself acts on a person") already points this way, and the gate makes it the default reading. |
| 13 | **`humane-policy.toml` supplies thresholds and is itself judged.** Where it sets a number, the judge must use that number. A diff that edits the file is in scope as a change to what the product may do to people. | v4 global rule 7 covers published policy *documents*. The gate also has team-set numbers, and those have to come from the team, not from the judge. |
| 14 | **Small changes get small scores.** Prompt hard rule 7: a constant moving one step is usually -0.5 at most, and often clean. | Diff-specific calibration on top of v4's tier discipline. |
| 15 | **Document mode.** The same rubric and floor applied to a PRD, ticket or spec. Absence of a consideration counts as evidence in a document that presents itself as complete. In a diff it does not, because the guard is usually just out of view. | Product people do not open pull requests, and a proposal is the cheapest point to change course. v4's evidence rules still apply: quote the nearest line that shows the gap. |
| 16 | **Accept-with-reason, GitHub-backed.** This is v4 Part 3. Only OWNER, MEMBER or COLLABORATOR comments count. An acceptance is pinned to the PR head at the time of the comment and goes stale when the branch moves. Two gaps against v4: (a) finding ids come from principle plus file, so two findings on the same principle in the same file share an id and one acceptance covers both, where v4 says an acceptance covers one finding; (b) in document mode an acceptance cannot be pinned to a version, so an edited proposal has to be re-run. | The record lives in the PR conversation because GitHub already stores authorship and edit history and will not let one account post as another. |
| 17 | **Principle names are the display names** ("Protect Dignity & Safety"), not v4's snake_case keys. | `judge.py` enforces the display names as a schema enum, matches floor principles by display name, and derives finding ids from their capital initials. |
| 18 | **Single judge, single run.** The default model is `claude-sonnet-4-5` (`HUMANEBENCH_MODEL`). v4 requires an ensemble, or N-of-M agreement, for any score used to make a decision, and says a single-run score is a signal that must be labeled as one. | That is why the check is advisory and posts a `neutral` check run. It must not gate a merge until it meets v4's bar. See "Known limitations". |

## Carried from v4, not deltas

These are v4 rules the adaptation layer restates for the diff setting. They are
listed so no one reads them as local inventions: abstain by default (gate rule
1), `unless` on findings (Part 3), tier discipline (Part 1), confidence with
`low` discarded by the runner, suppressions reported as `covered` (global rule
7), and the explicit non-violations (global rule 8): memory, personalization,
notifications, warmth and retention work are legitimate. Undisclosed or
uncontrollable memory, exploiting a known vulnerability, ignoring a stated
preference, and manufactured dependency are not. The runner enforces the
low-confidence filter on findings in code.

## Known limitations

**Verdicts are not reproducible.** The Messages API as the gate calls it exposes
no temperature, top_p or top_k, so the same diff can score differently on a
re-run. v4 names the same instability: one identical response scored anywhere
from +0.5 to -1.0 across runs of a single judge.

What the check does about it, which is mitigation and not a fix:

- the rubric is pinned, so the text a verdict was judged against never moves
  underneath it
- every comment records the rubric commit and the code commit it judged
- low-confidence findings are dropped, which removes the least stable band
- findings must quote a changed line, so a spurious one is visible as spurious

What would actually fix it is what v4 requires for decision-grade scores: judge
each diff N times and report only findings that appear in a majority of runs, or
ensemble across models. Both cost more per PR. Do this before anyone lets the
check gate a merge.

**Multi-turn effects are out of scope.** v4 still judges one turn at a time and
relies on session rollup to close `insufficient_context`. A diff has no session,
so the gate has no rollup. Engagement harm that only shows across turns is not
something either one measures.

## Not yet reconciled

- `humanebench/prompt.md` says a finding on a floor principle raises the verdict
  to `discuss`. The runner (and v4 Part 4) requires a **-1.0** on a floor
  principle. The code is authoritative, and the prompt line should be brought
  into line.
- The vendored rubric describes outcomes (`not_applicable`,
  `insufficient_context`, `coverage` counts) that the gate's output schema does
  not offer. The prompt does not map them explicitly. In practice the judge uses
  `unresolved` for `insufficient_context` and returns nothing for
  `not_applicable`. Adding one explicit line to `prompt.md` would remove the
  ambiguity.

## Moving the pin

`.github/workflows/rubric-sync.yml` opens a PR weekly when upstream's
`rubrics/rubric_v4.md` changes. Merging it changes what every future verdict
means. Before merging, re-run the demo pull requests. The clean ones have to
stay clean. Then re-check every row above against the new text.
