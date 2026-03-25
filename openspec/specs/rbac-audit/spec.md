# RBAC Audit

> Capability: `rbac-audit`
> Trigger: Timer — `0 0 8 * * *` (daily at 8 AM UTC)
> Source: `src/functions/audit_rbac.py`

## Requirements

### Requirement: Audit Fabric workspace access daily
The RBAC auditor SHALL query Fabric workspace role assignments daily at 8 AM UTC and evaluate each assignment against the allowed access policy.

#### Scenario: Timer fires
- **WHEN** the daily timer trigger fires
- **THEN** the auditor SHALL call `audit_workspace_access()` for the configured `FABRIC_WORKSPACE_ID`

### Requirement: Flag unauthorized privileged access
The auditor SHALL flag any principal with a privileged role (`Admin`, `Member`, or `Contributor`) that is not the Function App managed identity and not in the allowed access group.

#### Scenario: Unauthorized user with Admin role
- **WHEN** a user has the `Admin` role and is not in the allowed group or the managed identity
- **THEN** an `RbacViolation` SHALL be reported with reason `"Principal '{name}' has '{role}' role but is not in the allowed group '{group}'"`

#### Scenario: Managed identity has Contributor role
- **WHEN** the principal ID matches the `FUNCTION_APP_MANAGED_IDENTITY_ID`
- **THEN** the assignment SHALL be skipped (no violation)

#### Scenario: Allowed group has Admin role
- **WHEN** the principal name matches the `ALLOWED_RAW_ACCESS_GROUP`
- **THEN** the assignment SHALL be skipped (no violation)

### Requirement: Report compliance status
The auditor SHALL produce an `RbacAuditReport` with `workspace_id`, `checked_at`, `total_assignments`, `violations` list, and `is_compliant` boolean.

#### Scenario: All assignments compliant
- **WHEN** no violations are detected
- **THEN** `is_compliant` SHALL be `true` and the report SHALL be logged at INFO level

#### Scenario: Violations found
- **WHEN** one or more violations are detected
- **THEN** `is_compliant` SHALL be `false`, each violation SHALL be logged at WARNING level, and a summary SHALL be logged: `"RBAC audit FAILED for workspace {id} — {violations} violation(s) out of {total} assignments."`

### Requirement: Use environment variables for configuration
The auditor SHALL read configuration from environment variables.

#### Scenario: Configuration sources
- **WHEN** the auditor initializes
- **THEN** it SHALL read `FABRIC_WORKSPACE_ID`, `ALLOWED_RAW_ACCESS_GROUP` (default: `"IT-Admins"`), and `FUNCTION_APP_MANAGED_IDENTITY_ID` from environment variables
