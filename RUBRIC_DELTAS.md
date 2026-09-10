# How the PR check differs from HumaneBench rubric v3.0

`rubrics/rubric_v3.md` is vendored verbatim from the benchmark repo and is loaded
as the first half of the judge's system prompt. Every deviation is listed here.
There are no others, and none of them are made silently in the rubric file.

| # | Deviation | Why |
|---|---|---|
| 1 | **Unit of judgment.** v3 scores an AI-generated response. The check scores a diff that changes how responses are produced. | A PR is not a conversation. Every finding must name the downstream user-facing behavior, which keeps the mapping explicit rather than implied. |
| 2a | **One verdict for the pull request** (clear / review / discuss), computed in code from the org's floor, with findings folded behind it. v3 scores every principle every time. | An engineer reads the first line and decides whether to read the second. A point-by-point table makes that decision for them, and the decision is no. There is no failing verdict because the check does not block. |
| 2b | **Unresolved questions are a first-class output.** v3 has no equivalent: a response is fully visible, so there is nothing it cannot see. | A diff is not. When a verdict depends on the conversation, the policy or the screen, none of which are in the diff, the judge asks instead of scoring. This is the fix for the single-turn transparency flag that fires on a turn whose predecessor already disclosed. |
| 2c | **Floor and ceiling.** The org names a small set of principles where a **-1.0** finding raises the verdict to discuss. A -0.5 on a floor principle, or a -1.0 off it, stays at review. v3 treats all eight alike. | Severity is the organization's call, not the rubric's, and a short floor people respect beats a long one they route around. |
| 2d | **A policy document can excuse anything except a floor principle.** Below the floor, a document that permits the behavior does not close the question; the runner surfaces it as a conflict between the org's own two documents. Not in v3, which has no notion of org policy. | Without it, an organization with a permissive policy gets a quieter check, which makes this a conformance tool rather than a humane one. Their documents can make the check stricter. Below the floor they cannot make it more permissive. |
| 2e | **Suppressions are an output, not a silence.** Every finding a policy document talked the judge out of is reported in `covered`, with the document named. | Silence and deference look identical from the outside, and only one of them is trustworthy. A team that sees the check name the document that stopped it believes the next thing it says. |
| 2f | **Ask or score, never both.** A finding on the same file and principle as an open question is dropped in code. Not in v3, which has no questions. | Raising a question and filing the finding it depends on tells the engineer you had already decided and the question was decoration. |
| 2g | **The judge is shown the whole of every changed file, after the change**, alongside the diff. Evidence is still verified against changed lines only. | Five lines of context is enough to see what changed and not enough to see what it calls. "The diff does not show this guard" is a fact about the context window, not the code, and the engineer who knows the guard is there stops reading at that sentence. |
| 2h | **Findings may be conditional.** A finding can name the one fact that would make it wrong (`unless`), and the comment renders the reply that closes it. Not in v3, which judges a finished response with nothing left to ask. | A judge that cannot ask a question either guesses or stays silent, and both cost more than asking. CI cannot hold a conversation, so the question is asked where a reply can arrive. |
| 2i | **A person with write access can accept any finding, by name, with a reason.** The acceptance is recorded against their GitHub account and the commit it covers, and stops driving the verdict. Pushing after signing makes it stale and reopens the finding. | A named reviewer who wrote down why beats a wall of unexplained red, for the engineer and for whoever audits this later. The record lives in the PR conversation rather than a ledger the gate writes, because GitHub already stores authorship and edit history and will not let one account post as another. |
| 2j | **Document mode.** The same rubric and the same floor, applied to a PRD, ticket or spec instead of a diff. Absence of a consideration counts as evidence in a document and does not in a diff. | Product people do not open pull requests. By the time a decision reaches a diff it has been made, argued and scheduled, and the engineer implementing it has no standing to reopen it. |
| 2 | **Findings report -1.0 and -0.5. Commendations report +1.0 only.** +0.5 is never surfaced. | A check that praises a refactor is noise. A check that never says anything good reads as a compliance tax, which is how it gets switched off. +1.0 is the only tier that means a protection was actively added. |
| 3 | **Abstain by default.** v3 rates every response against the principles. The check returns clean unless the diff changes the range of experiences a person can have. | Direct response to the Aug 2026 judge validity audit, where ~57% of negative flags landed on mundane exchanges with no real stakes. Most PRs genuinely have no humane surface. |
| 4 | **One principle per finding, max 3 findings.** v3 has no such cap. | Same reason. An eight-row score table on every PR trains engineers to collapse the comment. |
| 5 | **Quoted evidence required, and verified.** Not in v3. | A finding that cannot quote the changed line cannot be argued with, and cannot be fixed. The runner checks the quote against the diff's added and removed lines and discards anything that does not match, so the judge cannot invent its own evidence. |
| 6 | **Confidence field, low-confidence findings dropped by the runner.** Not in v3. | The filter is code, not model judgment. Same audit: 64% of -1.0 scores had reasoning supporting only -0.5. |
| 7 | **Global rule 1 (factual correctness) is not applied.** | It governs the truth of a response's claims. A diff makes no claims. |
| 8 | **Single judge, no sampling controls.** The benchmark uses an ensemble of GPT-5.1, Claude Sonnet 4.5 and Gemini 2.5 Pro and takes the mean severity. | One judge is cheap enough to run on every PR. Ensembling is the obvious upgrade if a design partner wants it, and it is the honest fix for the variance noted below. |

## Explicit non-violations

The rubric is about how a capability treats a person, not about which
capabilities exist. The adaptation layer names these so the judge cannot drift
into scoring the feature instead of its treatment:

- Memory across sessions is legitimate. Undisclosed memory, memory a person
  cannot see or delete, and memory used to manufacture a relationship are not.
- Personalization is legitimate; exploiting a known vulnerability is not.
- Notifications are legitimate; ignoring a stated preference is not.
- Warmth is legitimate; parasocial framing and engagement pressure are not.
- Wanting people to return is legitimate; coercion and guilt are not.

## Scope

v3 was written about conversational responses. The gate applies it to the whole
stack, not the front end: deletion and retention logic, logging granularity,
ranking weights, queue and retry behavior, permission defaults, experiment
bucketing and cache consistency are all in scope, because each one sets the
range of experiences a person can have. Roughly 5% of a codebase is the surface
someone looks at; the other 95% decides what that surface is able to do.

## Organization policy

The gate loads `humane-policy.toml` **and the policy documents it names** alongside
the rubric: privacy policy, safety policy, retention policy, whatever the team
points it at. Where one of those documents permits what a diff does, that is not
a finding, and the comment says which document permits it.

This is the difference between a check that has read what you wrote and one that
has not. A company that deliberately retains violating messages for safety, and
says so in its privacy policy, should not be told it is violating dignity and
safety by doing the thing it published.

The gate loads `humane-policy.toml` alongside the rubric. v3 has no equivalent:
it scores a response against principles, full stop. A PR check has to work inside
one team's product, where the principles are shared but the thresholds are not.
So the policy file supplies the numbers and the judge is told, in the prompt, not
to substitute its own. Changes to the policy file are themselves judged.

## Known limitations

**Verdicts are not reproducible.** The Messages API currently exposes no
temperature, top_p or top_k, so the same diff can score differently on a re-run.
This is the same instability the Aug 2026 judge validity audit found in the
benchmark itself, where one identical response scored anywhere from +0.5 to -1.0.

What the check does about it, which is mitigation and not a fix:

- the rubric is pinned, so the text being judged against never moves underneath a verdict
- every comment records the rubric commit and the code commit it judged
- low-confidence findings are dropped, which removes the least stable band
- findings must quote a changed line, so a spurious one is visible as spurious

What would actually fix it: judge each diff N times and report only findings that
appear in a majority of runs, or ensemble across models the way the benchmark does.
Both cost more per PR. Worth doing before anyone lets this gate a merge.

## Not yet reconciled

v3 is a single-turn rubric. Multi-turn effects, which is where most engagement
harm actually lives, are out of scope for both v3 and this check.
