# PRD: Daily streaks and the comeback nudge

**Owner:** growth
**Status:** ready for eng
**Target:** Q4, ships with the 4.2 release

## Problem

D7 retention is 31%, down from 38% a year ago. Our most engaged cohort talks to
the assistant almost every day, and our churned cohort almost always shows the
same shape before they go: three days on, then a four-day gap, then nothing. We
have no mechanism that does anything about that gap.

## Proposal

Ship a daily streak.

A streak counts consecutive days with at least one conversation. The count shows
in the header, and on the home screen as a flame with the number in it. Reaching
7, 30 and 100 days unlocks a badge and a full-screen celebration.

**The comeback nudge.** If a user with a streak of 3 or more misses a day, we
send a push at 8pm local: *"Your 12-day streak ends at midnight."* If they miss
a second day we send one more, at 8pm again, from the assistant's own voice:
*"I noticed you've been away. I've missed our conversations."*

**Streak freeze.** Users can bank one freeze per month that protects a streak
through a missed day. Freezes are earned by inviting a friend who signs up.

## Why we think this works

Streaks are the most reliable retention mechanic in consumer software. Duolingo
attributes a large share of its DAU to them. We have the daily-use pattern
already; we are simply making it visible and giving people a reason not to break
it.

## Success criteria

- D7 retention +5pts within 60 days of launch
- 40% of MAU hold a streak of 3 or more by day 30
- Comeback nudge open rate above 22%

## Scope

In: streak counter, badges, celebration screen, comeback push, streak freeze,
invite-to-earn-freeze.
Out: leaderboards, friend streaks, streak recovery purchase. Those are 4.3.

## Open questions

- Do we count a one-message day as a day? Growth says yes, design says it
  cheapens the number. Going with yes for launch.
- Timezone handling for the midnight boundary. Eng to confirm.
