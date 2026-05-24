---
name: terraform-module-scaffold
description: "Scaffold and enforce standards for Terraform modules with compliance, cost, and operational patterns baked in. Use when creating a new Terraform module, scaffolding infrastructure for a new service, enforcing module conventions, reviewing module structure, adding infrastructure for databases, monitoring, event streaming, or any IaC work. Produces production-ready module skeletons with validation, testing, compliance tagging, and cost optimization built in."
---

## PE-Backed Financial Services Infrastructure Context

### Compliance Tagging Requirements
Every resource in a regulated financial services environment must carry these tags beyond the standard set:

```hcl
locals {
  compliance_tags = {
    data_classification = var.data_classification  # "public", "internal", "confidential", "restricted"
    regulatory_scope    = var.regulatory_scope      # "pci-dss", "sox", "glba", "none"
    pii_indicator       = var.contains_pii          # "true", "false"
    audit_required      = var.audit_required         # "true", "false"
    cost_center         = var.cost_center            # maps to PE financial reporting
    backup_tier         = var.backup_tier            # "critical-4hr", "standard-24hr", "archive-72hr"
  }
}

variable "data_classification" {
  type        = string
  description = "Data classification level per information security policy"
  validation {
    condition     = contains(["public", "internal", "confidential", "restricted"], var.data_classification)
    error_message = "Must be one of: public, internal, confidential, restricted."
  }
}

variable "regulatory_scope" {
  type        = string
  description = "Primary regulatory framework this resource falls under"
  default     = "none"
  validation {
    condition     = contains(["pci-dss", "sox", "glba", "state-lending", "none"], var.regulatory_scope)
    error_message = "Must be one of: pci-dss, sox, glba, state-lending, none."
  }
}
```

### Cost Optimization Patterns
PE sponsors expect infrastructure cost visibility and reduction:

```hcl
# Every module must output cost-relevant metadata
output "cost_metadata" {
  description = "Cost tracking metadata for FinOps reporting"
  value = {
    estimated_monthly_cost = var.environment == "production" ? "see cost estimate" : "non-prod"
    instance_family        = var.instance_type
    storage_gb             = var.storage_size
    cost_center            = var.cost_center
    can_use_reserved       = var.environment == "production" ? true : false
    can_use_spot           = var.workload_type == "batch" ? true : false
    auto_shutdown          = var.environment != "production" ? true : false
  }
}

# Non-production auto-shutdown pattern
resource "aws_autoscaling_schedule" "shutdown" {
  count                  = var.environment != "production" ? 1 : 0
  scheduled_action_name  = "nightly-shutdown"
  min_size               = 0
  max_size               = 0
  desired_capacity       = 0
  recurrence             = "0 22 * * MON-FRI"  # 10 PM weekdays
  autoscaling_group_name = aws_autoscaling_group.this.name
}
```

### Financial Services Encryption Standards
```hcl
# All data-at-rest must use customer-managed KMS keys (not AWS-managed)
# Required for PCI-DSS and SOX audit trail

variable "kms_key_arn" {
  type        = string
  description = "Customer-managed KMS key ARN. AWS-managed keys are not acceptable for regulated workloads."
  validation {
    condition     = can(regex("^arn:aws:kms:", var.kms_key_arn))
    error_message = "Must be a valid KMS key ARN. AWS-managed keys are not permitted."
  }
}

# Enforce encryption everywhere
check "encryption_at_rest" {
  assert {
    condition     = var.kms_key_arn != ""
    error_message = "All resources storing data must use customer-managed KMS encryption."
  }
}
```

---

# Terraform Module Standards

Your documented patterns based on 80+ sessions across database, infrastructure, monitoring, and event-streaming modules.

---

## Universal Conventions (All Modules)

### File Structure

```
module-name/
├── README.md              # Required: usage, examples, inputs/outputs
├── variables.tf           # Required: all inputs with validation
├── outputs.tf             # Required: all outputs with descriptions
├── main.tf                # Required: primary resource definitions
├── versions.tf            # Required: provider and Terraform constraints
├── data.tf                # Optional: data sources
├── locals.tf              # Optional: local values and computed values
├── examples/              # Optional but recommended
│   └── basic/             # Minimal working example
├── tests/                 # Required: *.tftest.hcl or similar
│   └── module.tftest.hcl  # Primary test file
└── modules/               # Optional: nested submodules
    └── submodule/
        ├── README.md
        ├── variables.tf
        ├── outputs.tf
        └── main.tf
```

### Variable Naming Conventions

**Required Variables (no defaults):**
- Use descriptive names indicating purpose
- Prefix with resource type for clarity: `cluster_name`, `instance_count`
- Never use single letters except in loops

```hcl
variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}
```

**Optional Variables (with defaults):**
- Provide sensible defaults for common cases
- Use `null` for optional features (not empty strings)
- Document what `null` means in the description

```hcl
variable "backup_retention_days" {
  description = "Number of days to retain backups. Set to null to disable backups."
  type        = number
  default     = 7
}
```

**Collection Variables:**
- Use `object({})` for structured data instead of loose maps
- Validate object structure with `validation` blocks
- Prefer lists for ordered collections, sets for uniqueness, maps for lookups

```hcl
variable "nodes" {
  description = "List of node configurations"
  type = list(object({
    name   = string
    cpu    = number
    memory = number
    disk   = optional(number, 100)
  }))
  default = []
}
```

### Output Conventions

**Naming:**
- Use resource identifier prefix: `db_endpoint`, `cluster_id`, `queue_url`
- Sensitive outputs must be marked: `sensitive = true`
- Always include descriptions explaining usage

```hcl
output "connection_string" {
  description = "PostgreSQL connection string (sensitive)"
  value       = "postgresql://${var.username}:${random_password.password.result}@${aws_db_instance.main.endpoint}/${var.database}"
  sensitive   = true
}

output "cluster_status" {
  description = "Current status of the cluster for health checks"
  value       = aws_rds_cluster.main.status
}
```

**Output Structure:**
- Group related outputs in maps for cleaner consumption
- Include metadata outputs for debugging: `arn`, `id`, `endpoint`

```hcl
output "cluster_info" {
  description = "Map of cluster metadata"
  value = {
    id       = aws_rds_cluster.main.id
    arn      = aws_rds_cluster.main.arn
    endpoint = aws_rds_cluster.main.endpoint
    port     = aws_rds_cluster.main.port
  }
}
```

### Resource Naming

**Internal Resource Names:**
- Use snake_case for all Terraform identifiers
- Prefix with module purpose: `pg_cluster`, `kafka_topic`, `datadog_monitor`
- Avoid generic names like `main`, `this`, `resource`

```hcl
resource "aws_db_instance" "pg_primary" {
  # ...
}

resource "aws_db_instance" "pg_replica" {
  # ...
}
```

**External Resource Names (Name Tags):**
- Format: `{environment}-{service}-{identifier}`
- Include random suffix for uniqueness: `substr(random_id.suffix.hex, 0, 8)`
- Keep under 63 characters for DNS compatibility

```hcl
locals {
  name_prefix = "${var.environment}-${var.service_name}"
  unique_name = "${local.name_prefix}-${substr(random_id.suffix.hex, 0, 8)}"
}

resource "aws_db_instance" "pg_primary" {
  identifier = local.unique_name
  # ...
}
```

### Tagging Strategy

**Mandatory Tags (all resources):**

```hcl
locals {
  common_tags = {
    Environment = var.environment
    Service     = var.service_name
    ManagedBy   = "terraform"
    Module      = "tf-module-name"  # Name of this module
    Owner       = var.team_owner
  }
}

resource "aws_db_instance" "example" {
  # ...
  tags = merge(local.common_tags, var.additional_tags)
}
```

**Tag Sanitization:**
- Enforce tag value constraints (no special chars, length limits)
- Use `replace()` or regex to sanitize dynamic tag values
- Document tag constraints in variable descriptions

```hcl
variable "additional_tags" {
  description = "Additional tags to apply. Tag values will be sanitized to remove special characters."
  type        = map(string)
  default     = {}

  validation {
    condition     = alltrue([for k, v in var.additional_tags : length(v) <= 255])
    error_message = "Tag values must be 255 characters or less."
  }
}

locals {
  # Sanitize tag values - remove characters that cause issues
  sanitized_tags = {
    for k, v in var.additional_tags :
    k => replace(v, "/[^a-zA-Z0-9\\s._:/=+@-]/", "")
  }
}
```

### Validation Patterns

**Variable Validation:**
- Always validate enum-like values with `contains()`
- Use regex for format validation (ARNs, names, etc.)
- Validate numeric ranges for sizing parameters

```hcl
variable "instance_type" {
  description = "Instance type for the cluster"
  type        = string

  validation {
    condition     = can(regex("^db\\.[tr]\\d", var.instance_type))
    error_message = "Instance type must be a valid RDS instance class (db.t*, db.r*)."
  }
}

variable "port" {
  description = "Database port number"
  type        = number
  default     = 5432

  validation {
    condition     = var.port > 1024 && var.port < 65535
    error_message = "Port must be between 1024 and 65535."
  }
}
```

**Check Blocks (Post-Apply Validation):**
- Use `check` blocks for assertions that can't be validated at plan time
- Include warning messages for deprecation notices
- Validate architecture compliance

```hcl
check "lambda_python_architecture" {
  assert {
    condition     = try(startswith(var.runtime, "python"), false) ? false : true
    error_message = "Please migrate your python lambda to a containerized arm64 deployment. DANGER: Upgrading requires lambda changes, pipeline changes, and downtime."
  }
}
```

**Preconditions:**
- Use `precondition` blocks for lifecycle validations
- Validate dependencies between variables

```hcl
resource "aws_db_instance" "replica" {
  # ...
  
  lifecycle {
    precondition {
      condition     = var.source_db_instance != null || var.replicate_source_db != null
      error_message = "Replica requires either source_db_instance or replicate_source_db to be set."
    }
  }
}
```

### Testing Approach

**OpenTofu/Terraform Test (*.tftest.hcl):**

```hcl
# tests/module.tftest.hcl

variables {
  environment = "test"
  service_name = "test-service"
}

run "setup" {
  module {
    source = "./"
  }
}

run "validate_defaults" {
  assert {
    condition     = output.cluster_info.port == 5432
    error_message = "Default port should be 5432"
  }
}

run "validate_with_custom_port" {
  variables {
    port = 5433
  }
  
  assert {
    condition     = output.cluster_info.port == 5433
    error_message = "Custom port should be respected"
  }
}

run "validate_invalid_port_fails" {
  variables {
    port = 100
  }
  
  expect_failures = [
    var.port
  ]
}
```

**Python Tests (for AWX/Complex modules):**

```python
# scripts/tests/test_module.py

import pytest
from unittest.mock import patch, MagicMock


def test_resource_creation_success(monkeypatch):
    # Set environment variables
    monkeypatch.setenv("API_URL", "https://api.example.com")
    monkeypatch.setenv("API_KEY", "test-key")
    
    # Mock API responses
    def mock_urlopen(request):
        return make_http_response({"status": "success", "id": "123"})
    
    monkeypatch.setattr("module_name.urlopen", mock_urlopen)
    
    # Test logic
    result = module_name.create_resource("test")
    assert result["id"] == "123"


def test_validation_error_handling():
    with pytest.raises(ValueError) as exc_info:
        module_name.validate_input(invalid_data)
    
    assert "validation failed" in str(exc_info.value)
```

**Test Organization:**
- Place tests in `tests/` subdirectory
- Name test files: `{module}.tftest.hcl` or `test_{module}.py`
- Include integration tests in CI (validate, plan, apply to ephemeral env)
- Run `tofu test` or `terraform test` in CI pipeline

### Documentation Standards

**README.md Structure:**

```markdown
# Terraform Module: [Name]

[Brief description of what this module creates]

## Features

- [Key feature 1]
- [Key feature 2]
- [Key feature 3]

## Usage

### Basic Example

```hcl
module "example" {
  source = "path/to/module"
  
  environment  = "prod"
  service_name = "my-service"
  
  # Required variables
  cluster_size = 3
}
```

### Advanced Example

```hcl
module "example" {
  source = "path/to/module"
  
  environment  = "prod"
  service_name = "my-service"
  
  # Sizing
  instance_type = "db.r5.2xlarge"
  storage_gb    = 500
  
  # Features
  enable_monitoring = true
  backup_retention_days = 14
  
  # Access control
  allowed_cidr_blocks = ["10.0.0.0/8"]
}
```

## Requirements

| Name | Version |
|------|---------|
| terraform | >= 1.5.0 |
| aws | >= 5.0.0 |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| environment | Environment name | `string` | n/a | yes |
| service_name | Service identifier | `string` | n/a | yes |
| instance_type | Instance size | `string` | `"db.t3.medium"` | no |
| ... | ... | ... | ... | ... |

## Outputs

| Name | Description | Sensitive |
|------|-------------|-----------|
| connection_string | Database connection string | yes |
| endpoint | Service endpoint | no |
| ... | ... | ... |

## Tagging

This module applies the following tags to all resources:

- `Environment`: From `var.environment`
- `Service`: From `var.service_name`
- `ManagedBy`: `"terraform"`
- `Owner`: From `var.team_owner`

Additional tags can be provided via `var.additional_tags`.

## Testing

Run tests with:

```bash
tofu test  # or terraform test
```

## Changelog

### v1.2.0
- Added support for [feature]

### v1.1.0
- Fixed [issue]

### v1.0.0
- Initial release
```

**Inline Comments:**
- Use comments to explain *why*, not *what*
- Document workarounds and TODOs with issue references
- Mark temporary solutions explicitly

```hcl
# NOTE: This is a workaround for AWS provider issue #12345
# Remove once provider supports native feature
locals {
  workaround_value = can(regex("...", var.input)) ? var.input : "default"
}

# TODO(terraform-upgrade): Replace with native validation when upgrading to TF 1.6+
# See: https://github.com/hashicorp/terraform/issues/xyz
```

---

## Domain-Specific Patterns

### Database Modules (PostgreSQL, RDS, ElastiCache)

**Sizing Pattern (T-Shirt Sizing):**

```hcl
variable "sizing_tier" {
  description = "T-shirt sizing tier: xsmall, small, medium, large, xlarge"
  type        = string
  default     = "small"

  validation {
    condition     = contains(["xsmall", "small", "medium", "large", "xlarge"], var.sizing_tier)
    error_message = "Sizing tier must be xsmall, small, medium, large, or xlarge."
  }
}

locals {
  sizing_config = {
    xsmall  = { cpu = 2, memory = 8, storage = 100 }
    small   = { cpu = 4, memory = 16, storage = 250 }
    medium  = { cpu = 8, memory = 32, storage = 500 }
    large   = { cpu = 16, memory = 64, storage = 1000 }
    xlarge  = { cpu = 32, memory = 128, storage = 2000 }
  }
  
  computed_cpu     = local.sizing_config[var.sizing_tier].cpu
  computed_memory  = local.sizing_config[var.sizing_tier].memory
  computed_storage = var.custom_storage_gb != null ? var.custom_storage_gb : local.sizing_config[var.sizing_tier].storage
}
```

**Access Control Pattern:**

```hcl
variable "access_groups" {
  description = "LDAP/AD groups with database access"
  type = object({
    superusers = list(string)
    read_write = list(string)
    read_only  = list(string)
  })
  default = {
    superusers = []
    read_write = []
    read_only  = []
  }
}
```

**Feature Flag Pattern:**

```hcl
variable "features" {
  description = "Feature flags for optional functionality"
  type = object({
    enable_replication     = optional(bool, false)
    enable_monitoring      = optional(bool, true)
    enable_data_masking    = optional(bool, false)
    enable_logical_replication = optional(bool, false)
  })
  default = {}
}
```

### Infrastructure/VM Modules (vSphere, Baremetal)

**Multi-Provider Abstraction:**

```hcl
variable "provider_type" {
  description = "Infrastructure provider: vsphere, baremetal, cloud"
  type        = string
  default     = "vsphere"
}

locals {
  is_vsphere   = var.provider_type == "vsphere"
  is_baremetal = var.provider_type == "baremetal"
  is_cloud     = var.provider_type == "cloud"
}

resource "vsphere_virtual_machine" "vm" {
  count = local.is_vsphere ? var.instance_count : 0
  
  # vSphere-specific configuration
}

resource "null_resource" "baremetal" {
  count = local.is_baremetal ? var.instance_count : 0
  
  # Baremetal provisioning via AWX/Ansible
  triggers = {
    playbook = file("${path.module}/templates/baremetal.yml")
  }
}
```

**AWX Integration Pattern:**

```hcl
resource "awx_job_template" "provisioning" {
  name         = "${local.name_prefix}-provision"
  job_type     = "run"
  inventory_id = var.awx_inventory_id
  project_id   = var.awx_project_id
  playbook     = "site.yml"
  
  extra_vars = jsonencode({
    node_name      = local.unique_name
    cpu_cores      = var.cpu_cores
    memory_gb      = var.memory_gb
    disk_gb        = var.disk_gb
    environment    = var.environment
  })
}
```

### Monitoring Modules (Datadog)

**Monitor Configuration Pattern:**

```hcl
variable "monitors" {
  description = "Map of monitor configurations"
  type = map(object({
    name        = string
    query       = string
    message     = string
    priority    = optional(number, 3)
    tags        = optional(list(string), [])
    thresholds  = optional(map(number), {})
    enabled     = optional(bool, true)
  }))
  default = {}
}

resource "datadog_monitor" "this" {
  for_each = var.monitors
  
  name    = each.value.name
  type    = "metric alert"
  query   = each.value.query
  message = each.value.message
  
  priority = each.value.priority
  
  tags = concat(
    [
      "env:${var.environment}",
      "service:${var.service_name}",
      "managed_by:terraform"
    ],
    each.value.tags
  )
  
  monitor_thresholds {
    warning           = lookup(each.value.thresholds, "warning", null)
    warning_recovery  = lookup(each.value.thresholds, "warning_recovery", null)
    critical          = lookup(each.value.thresholds, "critical", null)
    critical_recovery = lookup(each.value.thresholds, "critical_recovery", null)
  }
  
  enabled = each.value.enabled
}
```

### Event Streaming Modules (Kafka, Confluent)

**Connector Configuration Pattern:**

```hcl
variable "connectors" {
  description = "List of Kafka Connect connectors to deploy"
  type = list(object({
    name        = string
    class       = string
    tasks_max   = optional(number, 1)
    config      = map(string)
    
    # Lifecycle
    pause_on_deploy = optional(bool, false)
  }))
  default = []
}

locals {
  # Sanitize connector names for resource naming
  connector_resources = {
    for c in var.connectors :
    replace(lower(c.name), " ", "_") => c
  }
}

resource "confluent_connector" "this" {
  for_each = local.connector_resources
  
  environment {
    id = var.confluent_environment_id
  }
  
  kafka_cluster {
    id = var.kafka_cluster_id
  }
  
  # Configuration
  config_nonsensitive = each.value.config
  
  # Lifecycle management
  lifecycle {
    ignore_changes = [
      # Ignore runtime state changes
      config_nonsensitive["tasks.max"]
    ]
  }
}
```

**Topic Configuration Pattern:**

```hcl
variable "topics" {
  description = "List of Kafka topics to create"
  type = list(object({
    name               = string
    partitions         = number
    replication_factor = number
    config             = optional(map(string), {})
    
    # Access control
    producers = optional(list(string), [])
    consumers = optional(list(string), [])
  }))
  default = []
}

resource "confluent_kafka_topic" "this" {
  for_each = { for t in var.topics : t.name => t }
  
  topic_name         = each.value.name
  partitions_count   = each.value.partitions
  replication_factor = each.value.replication_factor
  
  config = merge(
    {
      "cleanup.policy" = "delete"
      "retention.ms"   = "604800000"  # 7 days
    },
    each.value.config
  )
}
```

---

## Starter Template/Scaffold

Use this as the foundation for new modules:

```hcl
#============================================================
# Module: {NAME}
# Description: {BRIEF DESCRIPTION}
#============================================================

#------------------------------------------------------------
# Versions
#------------------------------------------------------------
terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    {provider} = {
      source  = "hashicorp/{provider}"
      version = ">= 5.0.0"
    }
  }
}

#------------------------------------------------------------
# Locals
#------------------------------------------------------------
locals {
  # Naming
  name_prefix = "${var.environment}-${var.service_name}"
  unique_name = "${local.name_prefix}-${substr(random_id.suffix.hex, 0, 8)}"
  
  # Common tags
  common_tags = {
    Environment = var.environment
    Service     = var.service_name
    ManagedBy   = "terraform"
    Module      = "tf-{name}"
    Owner       = var.team_owner
  }
  
  # Sanitized tags
  sanitized_tags = {
    for k, v in var.additional_tags :
    k => replace(v, "/[^a-zA-Z0-9\\s._:/=+@-]/", "")
  }
  
  # Computed values
  effective_count = var.enabled ? var.instance_count : 0
}

resource "random_id" "suffix" {
  byte_length = 4
}

#------------------------------------------------------------
# Primary Resources
#------------------------------------------------------------
# TODO: Add main resources here

#------------------------------------------------------------
# Supporting Resources (IAM, Security Groups, etc.)
#------------------------------------------------------------
# TODO: Add supporting resources

#------------------------------------------------------------
# Data Sources
#------------------------------------------------------------
# TODO: Add data sources (usually in data.tf)
```

```hcl
#------------------------------------------------------------
# variables.tf
#------------------------------------------------------------

#------------------------------------------------------------
# Required Variables
#------------------------------------------------------------

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "service_name" {
  description = "Service identifier (kebab-case recommended)"
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]*$", var.service_name))
    error_message = "Service name must be lowercase alphanumeric with hyphens, starting with a letter."
  }
}

variable "team_owner" {
  description = "Team responsible for this resource"
  type        = string
}

#------------------------------------------------------------
# Optional Variables
#------------------------------------------------------------

variable "enabled" {
  description = "Set to false to disable resource creation"
  type        = bool
  default     = true
}

variable "instance_count" {
  description = "Number of instances to create"
  type        = number
  default     = 1

  validation {
    condition     = var.instance_count >= 0 && var.instance_count <= 10
    error_message = "Instance count must be between 0 and 10."
  }
}

variable "additional_tags" {
  description = "Additional tags to apply. Values will be sanitized."
  type        = map(string)
  default     = {}
}

#------------------------------------------------------------
# Feature Flags
#------------------------------------------------------------

variable "features" {
  description = "Feature flags for optional functionality"
  type = object({
    # TODO: Add feature flags
    enable_monitoring = optional(bool, true)
  })
  default = {}
}
```

```hcl
#------------------------------------------------------------
# outputs.tf
#------------------------------------------------------------

output "resource_info" {
  description = "Map of resource metadata"
  value = var.enabled ? {
    # TODO: Add resource metadata
    id   = {resource}.{name}.id
    arn  = {resource}.{name}.arn
    name = {resource}.{name}.name
  } : null
}

output "connection_info" {
  description = "Connection details (sensitive)"
  value       = var.enabled ? {resource}.{name}.endpoint : null
  sensitive   = true
}
```

```hcl
#------------------------------------------------------------
# tests/module.tftest.hcl
#------------------------------------------------------------

variables {
  environment  = "test"
  service_name = "test-service"
  team_owner   = "platform-team"
}

run "setup" {
  module {
    source = "./"
  }
}

run "validate_required_variables" {
  variables {
    environment  = "invalid"
    service_name = "TEST_service"  # Invalid format
  }
  
  expect_failures = [
    var.environment,
    var.service_name
  ]
}

run "validate_defaults" {
  assert {
    condition     = output.resource_info != null
    error_message = "Resource should be created with defaults"
  }
}
```

---

## Cross-Skill Integration

### When to Use This Skill
| Trigger Source | Scenario | Action |
|---|---|---|
| **architecture-assessor** | Infrastructure standards gap identified | Scaffold module that enforces the standard |
| **decision-engine** | ADR selects a new platform/service | Scaffold module for the selected option |
| **runbook-generator** | Deployment procedure needs codification | Module + runbook created in parallel |
| **migration-playbook** | Migration requires new infrastructure | Scaffold modules for target environment |
| Direct request | "Create a new module for X" | Standard scaffold workflow |

### Module Outputs Feed Other Skills
- **architecture-assessor** → Module quality and compliance tagging are assessment checklist items
- **runbook-generator** → Every module with `lifecycle` or `migration` patterns needs a companion runbook
- **vendor-evaluator** → Module provider dependencies inform vendor lock-in assessment
- **migration-playbook** → Migration infrastructure modules feed Phase 1 (Foundation) of migration plans

---

## Anti-Patterns (What to Avoid)

Based on patterns you've refactored away from:

### 1. Generic Resource Names

**❌ Bad:**
```hcl
resource "aws_db_instance" "this" { }
resource "aws_db_instance" "main" { }
```

**✅ Good:**
```hcl
resource "aws_db_instance" "pg_primary" { }
resource "aws_db_instance" "pg_replica" { }
```

### 2. Undocumented Variables

**❌ Bad:**
```hcl
variable "foo" {
  type = string
}
```

**✅ Good:**
```hcl
variable "backup_retention_days" {
  description = "Number of days to retain automated backups. Set to 0 to disable backups."
  type        = number
  default     = 7

  validation {
    condition     = var.backup_retention_days >= 0 && var.backup_retention_days <= 35
    error_message = "Backup retention must be between 0 and 35 days."
  }
}
```

### 3. Missing Validation

**❌ Bad:**
```hcl
variable "environment" {
  type    = string
  default = "dev"
}
```

**✅ Good:**
```hcl
variable "environment" {
  description = "Environment name"
  type        = string

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}
```

### 4. Hardcoded Values

**❌ Bad:**
```hcl
resource "aws_db_instance" "example" {
  instance_class = "db.t3.medium"  # Hardcoded
  allocated_storage = 100          # Hardcoded
}
```

**✅ Good:**
```hcl
variable "instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.medium"
}

variable "allocated_storage" {
  description = "Storage in GB"
  type        = number
  default     = 100
}

resource "aws_db_instance" "example" {
  instance_class    = var.instance_class
  allocated_storage = var.allocated_storage
}
```

### 5. Inconsistent Tagging

**❌ Bad:**
```hcl
resource "aws_db_instance" "example" {
  tags = {
    Name = "my-db"
    Env  = var.environment
  }
}

resource "aws_security_group" "example" {
  tags = {
    Name        = "my-sg"
    Environment = var.environment
  }
}
```

**✅ Good:**
```hcl
locals {
  common_tags = {
    Environment = var.environment
    Service     = var.service_name
    ManagedBy   = "terraform"
    Module      = "tf-module-name"
    Owner       = var.team_owner
  }
}

resource "aws_db_instance" "example" {
  tags = local.common_tags
}

resource "aws_security_group" "example" {
  tags = local.common_tags
}
```

### 6. No Test Coverage

**❌ Bad:** No tests directory

**✅ Good:**
```
module/
├── tests/
│   └── module.tftest.hcl
```

### 7. Missing Documentation

**❌ Bad:** No README or sparse inline comments

**✅ Good:** Full README with examples, requirements, inputs/outputs tables, changelog

### 8. Unstructured Data Types

**❌ Bad:**
```hcl
variable "config" {
  type = map(any)
}
```

**✅ Good:**
```hcl
variable "nodes" {
  type = list(object({
    name   = string
    cpu    = number
    memory = number
    disk   = optional(number, 100)
  }))
}
```

---

## Usage Workflow

### Creating a New Module

1. **Copy the starter template** from above
2. **Fill in TODOs**: Add resources, data sources, variables
3. **Add validation**: Every variable that accepts limited values
4. **Write tests**: At least validate defaults and error cases
5. **Write README**: Follow the documentation template
6. **Tag resources**: Apply mandatory tags + sanitization
7. **Version control**: Follow semantic versioning for releases

### Refactoring Existing Modules

1. **Audit current state**: List all violations of these standards
2. **Fix naming**: Rename resources to be descriptive
3. **Add validation**: Backfill validation blocks
4. **Structure files**: Split into data.tf, locals.tf if needed
5. **Add tests**: Create test coverage for critical paths
6. **Update docs**: Refresh README to match current state

### For Team Rollout

Share this document with:

> "This is our Terraform module standard. All new modules must follow these conventions. Existing modules should be refactored to comply during major version updates.
>
> Key principles:
> - Descriptive naming (never `this` or `main`)
> - Validation on all constrained inputs
> - Mandatory tags on all resources
> - Tests for all modules
> - Complete README documentation"

---

## Continuous Improvement

Update this skill as patterns evolve:

- New provider patterns discovered
- Testing framework improvements
- Team feedback on conventions
- Anti-patterns identified in reviews
