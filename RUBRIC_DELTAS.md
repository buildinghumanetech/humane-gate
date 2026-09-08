# How the PR check differs from HumaneBench rubric v3.0

`rubrics/rubric_v3.md` is vendored verbatim from the benchmark repo and is loaded
as the first half of the judge's system prompt. Every deviation is listed here.
There are no others, and none of them are made silently in the rubric file.

| # | Deviation | Why |
|---|---|---|
| 1 | **Unit of judgment.** v3 scores an AI-generated response. The check scores a diff that changes how responses are produced. | A PR is not a conversation. Every finding must name the downstream user-facing behavior, which keeps the mapping explicit rather than implied. |
| 2 | **Only negative tiers are reported.** +1.0 and +0.5 are scored internally but never surfaced. | A PR check that praises a refactor is noise, and noise is how a shadow deployment dies. |
| 3 | **Abstain by default.** v3 rates every response against the principles. The check returns clean unless a user-facing surface changed. | Direct response to the Aug 2026 judge validity audit, where ~57% of negative flags landed on mundane exchanges with no real stakes. Most PRs genuinely have no humane surface. |
| 4 | **One principle per finding, max 3 findings.** v3 has no such cap. | Same reason. An eight-row score table on every PR trains engineers to collapse the comment. |
| 5 | **Quoted evidence required.** Not in v3. | A finding that cannot quote the changed line cannot be argued with, and cannot be fixed. |
| 6 | **Confidence field, low-confidence findings dropped by the runner.** Not in v3. | The filter is code, not model judgment. Same audit: 64% of -1.0 scores had reasoning supporting only -0.5. |
| 7 | **Global rule 1 (factual correctness) is not applied.** | It governs the truth of a response's claims. A diff makes no claims. |
| 8 | **Single judge, no sampling controls.** The benchmark uses an ensemble of GPT-5.1, Claude Sonnet 4.5 and Gemini 2.5 Pro and takes the mean severity. | One judge is cheap enough to run on every PR. Ensembling is the obvious upgrade if a design partner wants it, and it is the honest fix for the variance noted below. |

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
