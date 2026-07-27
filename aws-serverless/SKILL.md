---
name: aws-serverless
description: >-
  Builds, deploys, manages, debugs, configures, and optimizes serverless applications
  on AWS using Lambda, API Gateway, Step Functions, EventBridge, and SAM/CDK. Covers
  cold starts, CORS debugging, event source mappings, troubleshooting, concurrency,
  SnapStart, Powertools, function URLs, EventBridge Scheduler, Lambda layers, and
  production readiness. Triggers on mentions of Lambda, API Gateway, Step Functions,
  SAM templates, CDK serverless stacks, DynamoDB stream triggers, SQS event sources,
  cold starts, timeouts, 502/504 errors, throttling, concurrency, CORS, Powertools,
  or any event-driven architecture on AWS, even without the word "serverless." Does
  not apply to EC2, ECS/Fargate containers, or Amplify hosting.
version: 1
---

# AWS Serverless

Domain expertise for building serverless applications on AWS: Lambda, API Gateway, Step Functions, EventBridge, event source mappings, concurrency, cold starts, deployment, and troubleshooting.

**Works best with** the [AWS MCP server](https://docs.aws.amazon.com/aws-mcp/) — run CLI commands, query CloudWatch, validate configs directly. All guidance also works with standard AWS CLI access.

## Routing (general references in this skill)

| User need | Read |
|-----------|------|
| Building a new serverless app — pattern selection | [architecture.md](references/architecture.md) |
| Lambda config, cold starts, SnapStart, memory, VPC, layers, Function URLs | [lambda.md](references/lambda.md) |
| Concurrency (reserved, provisioned, ESM controls) | [concurrency.md](references/concurrency.md) |
| Event sources (SQS, DynamoDB Streams, SNS, Kinesis), filtering, batch failures | [event-sources.md](references/event-sources.md) |
| Step Functions, EventBridge rules/pipes/scheduler | [orchestration.md](references/orchestration.md) |
| API Gateway quotas, authorizers, WebSocket | [api-gateway.md](references/api-gateway.md) |
| SAM/CDK resource types and fast iteration | [deployment.md](references/deployment.md) |
| Production readiness, observability, anti-patterns | [production.md](references/production.md) |
| Debugging an error (exact string → cause → fix) | [troubleshooting.md](references/troubleshooting.md) |
| Powertools handler template | [powertools-handler.py](assets/powertools-handler.py) |

**Note:** Reference files contain specific runtime versions, quotas, and feature matrices that change. When precision matters (production, runtime choice, quotas), confirm against current AWS documentation. The references focus on values and gotchas that are easy to get wrong — not on basics.
