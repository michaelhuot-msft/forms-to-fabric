# Form Activation

> Capability: `form-activation`
> Route: `POST /api/activate-form`
> Source: `src/functions/activate_form.py`

## Requirements

### Requirement: Require form_id
The endpoint SHALL require a `form_id` in the request body.

#### Scenario: Missing form_id
- **WHEN** `form_id` is not provided
- **THEN** the endpoint SHALL return HTTP `400`

### Requirement: Lookup form in registry
The endpoint SHALL look up the form in the registry and reject unknown forms.

#### Scenario: Form not found
- **WHEN** `form_id` does not exist in the registry
- **THEN** the endpoint SHALL return HTTP `404`

### Requirement: Handle already-active forms
The endpoint SHALL return success without modification when a form is already active.

#### Scenario: Form already active
- **WHEN** the form status is already `"active"`
- **THEN** the endpoint SHALL return HTTP `200` with message `"already active"`

### Requirement: Reject inactive forms
The endpoint SHALL not allow activation of forms with `"inactive"` status.

#### Scenario: Inactive form
- **WHEN** the form status is `"inactive"`
- **THEN** the endpoint SHALL return HTTP `400` with error `"cannot activate an inactive form"`

### Requirement: Validate PHI field configuration before activation
The endpoint SHALL verify that all PHI fields have a valid `deid_method` configured before transitioning to active.

#### Scenario: All PHI fields configured
- **WHEN** every field with `contains_phi=true` has `deid_method` set to `"hash"`, `"redact"`, or `"generalize"`
- **THEN** the form SHALL transition from `"pending_review"` to `"active"`

#### Scenario: Unconfigured PHI fields
- **WHEN** one or more fields with `contains_phi=true` lack a valid `deid_method`
- **THEN** the endpoint SHALL return HTTP `400` with error `"PHI fields missing deid_method configuration"` and an `unconfigured_fields` array

### Requirement: Transition pending_review to active
The only valid activation transition SHALL be `"pending_review"` → `"active"`. The endpoint SHALL save the registry and invalidate any cache.

#### Scenario: Successful activation
- **WHEN** a form in `"pending_review"` passes PHI validation
- **THEN** the status SHALL be set to `"active"`, the registry saved, and the cache invalidated
