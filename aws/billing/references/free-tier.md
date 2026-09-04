# Free Tier

## July 2025 Transition

AWS transitioned from time-based to credit-based free tier on July 15, 2025:

| Account Type | Model | Details |
|-------------|-------|---------|
| Legacy (before July 15, 2025) | 12-month offers + Always Free | Existing benefits continue under the legacy program. |
| Free Plan (after July 15, 2025) | $100 sign-up credit plus up to $100 earned credits | The plan ends after six months or when credits are exhausted, whichever comes first. The account then closes unless upgraded within 90 days. |
| Paid Plan (after July 15, 2025) | Same sign-up and earned-credit opportunity | Usage beyond credits is charged. Credits expire 12 months after account creation. |

AWS currently lists over 30 services with Always Free monthly usage limits. They remain available while the user is an AWS customer, but the offer list and limits can change. Verify the current service page before relying on an allowance.

## Recommended Workflow

1. First: `aws freetier get-account-plan-state` — determine account type and eligibility
2. Then: `aws freetier get-free-tier-usage` — check current usage for active services

## Critical Rules

- NEVER cite specific free tier limits from training data — offers changed July 15, 2025 and vary by account type
- `getFreeTierUsage` only returns services with usage > 0. Missing service means either no free tier offer exists OR customer hasn't used it yet.
- For questions about available offers before using a service, direct to https://aws.amazon.com/free/
- Legacy accounts: former 12-month services stop appearing after their period expires
- Free Plan/Paid Plan: $200 credit replaced 12-month offers. Always Free services tracked individually.

```bash
# Check account plan state
aws freetier get-account-plan-state

# Check current free tier usage
aws freetier get-free-tier-usage
```

Current references: [Choosing a plan](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-plans.html) and [AWS Free Tier FAQs](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-FAQ.html).
