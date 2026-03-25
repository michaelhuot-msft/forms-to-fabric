# Form Registry

> Capability: `form-registry`
> Config: `config/form-registry.json`
> Schema: `src/functions/form-registry.schema.json`

## Requirements

### Requirement: Root structure contains forms array
The registry file SHALL be a JSON object with a single `forms` key containing an array of `FormConfig` objects.

#### Scenario: Valid registry structure
- **WHEN** the registry file is loaded
- **THEN** it SHALL contain `{"forms": [...]}`

### Requirement: FormConfig required fields
Each form entry SHALL have `form_id` (string), `form_name` (string, max 50 chars), `target_table` (string, valid SQL identifier), `status` (string), and `fields` (array of `FieldConfig`).

#### Scenario: Valid form entry
- **WHEN** a form entry is read
- **THEN** `form_id`, `form_name`, `target_table`, `status`, and `fields` SHALL all be present

#### Scenario: target_table is valid SQL identifier
- **WHEN** `target_table` is validated
- **THEN** it SHALL match the pattern `^[a-zA-Z_][a-zA-Z0-9_]*$`

### Requirement: Valid form statuses
The `status` field SHALL be one of: `"active"`, `"pending_review"`, or `"inactive"`.

#### Scenario: Active form
- **WHEN** status is `"active"`
- **THEN** the form SHALL accept submissions via `/api/process-response`

#### Scenario: Pending review form
- **WHEN** status is `"pending_review"`
- **THEN** the form SHALL reject submissions with HTTP `403` until activated

#### Scenario: Inactive form
- **WHEN** status is `"inactive"`
- **THEN** the form SHALL reject submissions with HTTP `403` and cannot be activated

### Requirement: FieldConfig structure
Each field entry SHALL have `question_id` (string), `field_name` (string), `contains_phi` (boolean, default `false`), and optional `deid_method` (one of `"hash"`, `"redact"`, `"generalize"`, or `null`) and `field_type` (string or `null`).

#### Scenario: PHI field with de-identification
- **WHEN** a field has `contains_phi=true`
- **THEN** `deid_method` SHALL be set to `"hash"`, `"redact"`, or `"generalize"` before the form can be activated

#### Scenario: Non-PHI field
- **WHEN** a field has `contains_phi=false`
- **THEN** `deid_method` MAY be `null` and the value passes through unchanged

### Requirement: Unique form_id
Each `form_id` in the registry SHALL be unique.

#### Scenario: Duplicate form_id
- **WHEN** a new form is registered with an existing `form_id`
- **THEN** the registration endpoint SHALL return `"already_registered"` instead of creating a duplicate

### Requirement: Generalize requires field_type hint
When `deid_method` is `"generalize"`, a `field_type` SHOULD be specified for meaningful transformation.

#### Scenario: Generalize with field_type
- **WHEN** `deid_method="generalize"` and `field_type="age"`
- **THEN** the de-identification engine SHALL produce a decade range (e.g., `"30-39"`)

#### Scenario: Generalize without field_type
- **WHEN** `deid_method="generalize"` and `field_type` is `null`
- **THEN** the de-identification engine SHALL produce `"[GENERALIZED]"`
