---
name: aws
description: >-
  AWS infrastructure and AWS CLI operations: serverless (Lambda, API Gateway,
  Step Functions), containers (ECS, Fargate, ECR), delivery automation, networking,
  security operations, observability (CloudWatch, X-Ray, Application Signals),
  compute (EC2, Auto Scaling, SSM), messaging, billing, Bedrock, authentication,
  multi-account and multi-region inventory, shell automation, and safe AWS changes.
  Use for any AWS service, CLI command, CDK/SAM task, AWS error, audit, deployment,
  incident, network investigation, security control, or cost question.
---

# AWS

Umbrella skill for all AWS infrastructure and services. Routes queries to the appropriate
domain module based on topic.

## Routing

Identify which module(s) to load based on the user's question. Read ONLY the relevant
module; do not load all of them.

Before writing or executing any `aws` CLI command, read the shared
[CLI operating guide](references/cli-operating.md). Then read the service module or
reference needed for the task.

| Topic | Module | When to use |
|-------|--------|-------------|
| Lambda, API Gateway, Step Functions, EventBridge, SAM, cold starts, timeouts, CORS | [serverless/instructions.md](serverless/instructions.md) | Serverless apps, Lambda config, event-driven architecture |
| ECS, Fargate, ECR, task definitions, App Runner, container runtime | [containers/instructions.md](containers/instructions.md) | Container workloads and runtime behavior |
| GitHub Actions OIDC, ECR/ECS release, SSM fleet deploy, S3 publish, targeted apply, rollback | [delivery/instructions.md](delivery/instructions.md) | Delivering one verified revision to AWS |
| Transit Gateway, Route 53, Resolver, VPC endpoints, security groups, ALB listener rules | [networking/instructions.md](networking/instructions.md) | Cross-account network discovery and narrow network changes |
| GuardDuty, WAF evidence, CloudTrail data events, secret exposure, KMS and IAM checks | [security/instructions.md](security/instructions.md) | Security investigation, evidence, and approved containment |
| CloudWatch, X-Ray, Application Signals, ADOT, alarms, dashboards, Dynamic Instrumentation | [observability/instructions.md](observability/instructions.md) | Monitoring, tracing, metrics, debugging live services |
| EC2, Auto Scaling, AMI, launch templates, IMDSv2, SSM | [compute/instructions.md](compute/instructions.md) | Virtual machines, fleets, instance management |
| SQS, SNS, EventBridge, Kinesis, MSK, Amazon MQ | [messaging/instructions.md](messaging/instructions.md) | Queues, topics, streaming, event routing |
| Cost Explorer, Budgets, Savings Plans, Reserved Instances, CUR, pricing | [billing/instructions.md](billing/instructions.md) | Cost analysis, optimization, pricing lookup |
| Bedrock, Knowledge Bases, Agents, Guardrails, AgentCore, foundation models | [bedrock/instructions.md](bedrock/instructions.md) | Generative AI, foundation models, RAG |
| `aws login`, `aws sso login`, credentials, session expired, AccessDeniedException (no creds) | [auth/instructions.md](auth/instructions.md) | Getting AWS credentials for CLI/SDK |
| General AWS CLI operation, profiles, Regions, output, pagination, shell payloads, account sweeps, safe mutations | [references/cli-operating.md](references/cli-operating.md) | Cross-service CLI operating rules and proven command patterns |

## Multi-Domain Questions

Some questions span domains. Examples:

- "Lambda is slow" → start with `serverless`, may need `observability` for tracing
- "ECS task OOM" → `containers` has the answer, but if investigating metrics, also `observability`
- "Ship this image to ECS" → `delivery` owns release proof; `containers` owns runtime configuration
- "A public route exposes configuration" → `security` owns evidence; `networking` owns an approved listener change
- "How much does Fargate cost?" → `containers` for sizing, `billing` for pricing lookup
- "Sweep every account for this resource" → `cli-operating` for the safe loop, then the service module

Load the primary domain first. If it points you elsewhere or you need more context, load the second.

## Module Structure

Each subdirectory contains:
- `instructions.md`: the main skill content (formerly `SKILL.md`)
- `references/`: deeper documentation loaded on demand
- `scripts/`: helper scripts, if any
- `assets/`: templates and config files, if any

Root-level `references/` files contain rules shared by more than one service module.

## Fallback

If no module clearly matches, ask the user which AWS service they're working with.
