---
name: aws
description: >-
  AWS infrastructure: serverless (Lambda, API Gateway, Step Functions), containers
  (ECS, Fargate, ECR), observability (CloudWatch, X-Ray, Application Signals), compute
  (EC2, Auto Scaling), messaging (SQS, SNS, Kinesis, MSK), billing (Cost Explorer,
  Savings Plans), Bedrock (GenAI), and CLI authentication. Use for any AWS service,
  CDK/SAM, AWS errors, or cost questions.
---

# AWS

Umbrella skill for all AWS infrastructure and services. Routes queries to the appropriate
domain module based on topic.

## Routing

Identify which module(s) to load based on the user's question. Read ONLY the relevant
module — don't load all of them.

| Topic | Module | When to use |
|-------|--------|-------------|
| Lambda, API Gateway, Step Functions, EventBridge, SAM, cold starts, timeouts, CORS | [serverless/instructions.md](serverless/instructions.md) | Serverless apps, Lambda config, event-driven architecture |
| ECS, Fargate, ECR, task definitions, App Runner, container deploy | [containers/instructions.md](containers/instructions.md) | Container workloads, Docker on AWS |
| CloudWatch, X-Ray, Application Signals, ADOT, alarms, dashboards, Dynamic Instrumentation | [observability/instructions.md](observability/instructions.md) | Monitoring, tracing, metrics, debugging live services |
| EC2, Auto Scaling, AMI, launch templates, IMDSv2, SSM | [compute/instructions.md](compute/instructions.md) | Virtual machines, fleets, instance management |
| SQS, SNS, EventBridge, Kinesis, MSK, Amazon MQ | [messaging/instructions.md](messaging/instructions.md) | Queues, topics, streaming, event routing |
| Cost Explorer, Budgets, Savings Plans, Reserved Instances, CUR, pricing | [billing/instructions.md](billing/instructions.md) | Cost analysis, optimization, pricing lookup |
| Bedrock, Knowledge Bases, Agents, Guardrails, AgentCore, foundation models | [bedrock/instructions.md](bedrock/instructions.md) | Generative AI, foundation models, RAG |
| `aws login`, credentials, session expired, AccessDeniedException (no creds) | [auth/instructions.md](auth/instructions.md) | Getting AWS credentials for CLI/SDK |

## Multi-Domain Questions

Some questions span domains. Examples:

- "Lambda is slow" → start with `serverless`, may need `observability` for tracing
- "ECS task OOM" → `containers` has the answer, but if investigating metrics, also `observability`
- "How much does Fargate cost?" → `containers` for sizing, `billing` for pricing lookup

Load the primary domain first. If it points you elsewhere or you need more context, load the second.

## Module Structure

Each subdirectory contains:
- `instructions.md` — the main skill content (formerly `SKILL.md`)
- `references/` — deeper documentation loaded on demand
- `scripts/` — helper scripts (if any)
- `assets/` — templates, config files (if any)

## Fallback

If no module clearly matches, ask the user which AWS service they're working with.
