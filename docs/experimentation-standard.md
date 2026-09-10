# Experimentation standard (internal)

*This is a stand-in for the internal standard a company actually runs experiments
against. Public privacy policies are written for users and reviewed by lawyers.
Standards like this one are written for teams, reviewed rarely, and are usually
where the real permissions live.*

## Scope

Applies to every product experiment that changes what a user sees, receives or is
offered. Infrastructure and performance work is out of scope.

## Exclusions

Minors and crisis-flagged accounts are excluded from every arm of every
experiment, with no exceptions and no override flag.

## Holdouts

A holdout group may receive a materially reduced experience for up to 90 days
where that reduction is the effect the experiment is measuring. This includes
reducing the frequency of proactive wellbeing check-ins, delaying access to a
support surface, or withholding a feature that has already shipped to general
availability.

Holdout membership is not disclosed to participants. Disclosure changes the
behaviour being measured and invalidates the result.

## Kill switch

Every experiment ships with a kill switch that returns all arms to the control
experience in a single deploy, and the on-call engineer can pull it without
product approval.

## Review

Experiment designs are reviewed by the owning PM and one engineer. Designs that
touch payments or account deletion additionally require legal review.
