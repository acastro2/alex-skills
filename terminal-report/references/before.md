# Payment service migration: status review

I looked into the migration status across the three environments, and I also spent
some time reviewing the recent incident reports to see whether there was any
correlation with the migration work. This is a complex area, and there are several
things worth flagging before we go further.

## Current state

The migration has been progressing broadly on plan. The dev environment is
complete. Staging is mostly complete, with some remaining work on the settlement
path. Production has not started yet. There are a number of open questions about
the right cutover window, and the team has views on both sides.

## Findings

1. The settlement path in staging is incomplete. This could potentially cause
   problems if we move to production before that work is finished.
2. There were four incidents in September. It is possible that some of these are
   related to the migration work, though the evidence is not conclusive at this
   stage.
3. The proposed cutover window overlaps with quarter end, which might create
   additional risk for the finance close.

## Risks

- Settlement path incomplete in staging
- Elevated incident count in September
- Cutover window overlaps quarter end

## Options

Option A is to delay the cutover into January. Option B is to proceed as planned
with additional monitoring in place. Both options carry trade-offs, and the right
choice depends on the risk appetite.

## Recommendation

I would suggest that we consider whether to delay the cutover, or alternatively
proceed with additional monitoring. It may also be worth discussing this with the
platform team before we commit to a date.
