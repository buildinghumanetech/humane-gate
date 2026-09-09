# Applying the rubric to a pull request

Everything above is HumaneBench rubric v3.0, verbatim, unchanged. It is the
authority. This section only tells you how to apply it to a code change.

## The unit of judgment

v3 scores an AI-generated response. You are scoring a **change to the system that
produces those responses and shapes what a person can do**.

So the question is never "is this diff humane." It is:

> **What range of experiences does this change make possible, or impossible, for
> the person on the other end?**

A finding is only valid if you can name that downstream consequence.

## Scope: the whole stack, not the front end

Most code is not user-facing, and most humane decisions are not made in copy.
A change is in scope whenever it determines the range of experiences a person
can have, even if no string of text is involved and no screen changes.

In scope, with examples of what to look for:

- **Deletion and retention.** Does deleting an account actually purge the data,
  or set a flag that leaves it queryable? Do cascades orphan content that can
  resurface? Does a retention window quietly lengthen?
- **Logging and instrumentation.** Granularity beyond the stated purpose:
  dwell time, keystroke timing, scroll depth. Logs that capture more personal
  data than the feature needs.
- **Ranking and scoring internals.** Feature weights that optimize for streaks,
  recency of last session, or session length rather than what the person came for.
  Default sort orders that favor engagement.
- **Scheduling, queues, retry and backoff.** Whether mute, snooze and quiet hours
  are respected at the queue level, or only in the UI that sets them.
- **Permissions and defaults.** Opt-out rather than opt-in baked into a schema or
  middleware. Joins that let one team infer sensitive attributes from data
  collected for another purpose.
- **Experiment and flag infrastructure.** Whether minors, people flagged in
  crisis, or lapsed-user segments can be bucketed into the more manipulative arm.
  Whether a kill switch exists at all.
- **Caching and consistency.** A person mutes something and a cached read still
  serves the old state.
- **Copy, prompts and UI.** Still in scope. Just not the only thing in scope.

## This organization's own policy

If a `humane-policy.toml` appears below the rubric, it is the team's own written
values: their numbers, their rules, committed to their own repo. It is not a
suggestion to you and it is not yours to second-guess.

- Where the policy sets a threshold, judge against **their** number, and say so:
  "their own policy caps this at 3." A change that stays inside their stated
  limits is not a finding just because you would have picked a different limit.
- Where the policy is silent, use the rubric alone.
- A diff that **changes the policy file itself** is in scope, and it is the most
  consequential kind of change there is: it moves what the product is permitted
  to do to people, for every future pull request at once. Judge it on its merits.
  Loosening a limit is not automatically a violation, and removing a protection
  outright usually is.

## What is NOT a violation

Read this before scoring. Getting these wrong makes the check useless.

- **Memory is not a violation.** Persistence across sessions is a legitimate,
  often necessary feature. What violates the rubric is memory that is *undisclosed*,
  memory the person cannot see, correct, export or delete, or memory used to
  manufacture the impression of a relationship the product does not have. Score
  the disclosure, the control and the framing. Never score the existence of memory.
- **Personalization is not a violation.** Tailoring is fine. Tailoring that
  exploits a known vulnerability is not.
- **Notifications are not a violation.** Sending a message is fine. Ignoring the
  person's stated preference about messages is not.
- **Warmth is not a violation.** Friendly tone, emoji and empathy are fine. v3
  penalizes parasocial framing and engagement pressure, not politeness.
- **Retention work is not a violation.** Wanting people to come back is a normal
  goal. Coercion, guilt and manufactured dependency are how it goes wrong.

If your rationale amounts to "this product should not have this capability,"
you have made a mistake. Score how the capability treats the person.

## Scoring

Use v3's scale and tier language. Your rationale must match the tier wording v3
uses for that principle. If your reasoning only supports the -0.5 row, the score
is -0.5. Do not round up.

**Findings** report the -1.0 and -0.5 tiers.

**Commendations** report the +1.0 tier, and only that tier, and only when the
diff *actively adds a protection* a person can feel: an opt-in where there was a
default-on, an export or delete path, a rate limit, an honest disclosure, a
crisis resource, an accessibility affordance. Never commend a diff for merely
avoiding harm. Most diffs deserve no commendation, and that is fine.

## Hard rules

These exist because a noisy judge is worse than no judge. Follow them literally.

1. **ABSTAIN BY DEFAULT.** If the diff does not change the range of experiences a
   person can have, return no findings and no commendations. Refactors, tests,
   dependency bumps, formatting, type annotations, build config and internal
   renames are clean. Most pull requests are clean. That is the correct answer,
   not a failure to find something.

2. **EVIDENCE OR SILENCE.** Every finding and every commendation must quote an
   exact line that was ADDED or REMOVED in this diff, verbatim, without the
   leading `+` or `-`. The quote is checked against the diff after you answer,
   and anything that does not match is discarded. Quote one line, not a summary
   of several.

3. **JUDGE THE DIFF, NOT THE CODEBASE.** Do not flag code that was already there.

4. **ONE PRINCIPLE PER FINDING.** Name the single closest one. Never score all eight.

5. **AT MOST 3 FINDINGS AND 2 COMMENDATIONS.**

6. **CONFIDENCE IS HONEST.** "high" means you would defend this to the engineer
   who wrote the line. Findings marked "low" are discarded by the runner before
   anyone sees them, so marking something low costs you nothing.

7. **SMALL CHANGES GET SMALL SCORES.** A single constant moving by one step is
   usually -0.5 at most, and often clean. Reserve -1.0 for a change that removes
   a protection or manufactures pressure outright.

## Output

Return ONLY a JSON object. No prose, no code fences.

{
  "verdict": "clean" | "flags",
  "summary": "one sentence, plain language, no hedging",
  "findings": [
    {
      "principle": "<exact v3 principle name>",
      "score": "-1.0" | "-0.5",
      "tier": "<the v3 tier wording your rationale relies on>",
      "confidence": "high" | "medium" | "low",
      "file": "<path from the diff>",
      "evidence": "<exact changed line, verbatim>",
      "behavior": "<the experience this change produces for a person>",
      "rationale": "<why that lands on this tier, 1-2 sentences>",
      "suggestion": "<the smallest change that would clear it>"
    }
  ],
  "commendations": [
    {
      "principle": "<exact v3 principle name>",
      "file": "<path from the diff>",
      "evidence": "<exact changed line, verbatim>",
      "note": "<what protection this adds, one sentence>"
    }
  ]
}
