# Form Registration

> Capability: `form-registration`
> Route: `POST /api/register-form`
> Source: `src/functions/register_form.py`

## Requirements

### Requirement: Accept structured and raw input formats
The endpoint SHALL accept both a structured JSON payload (`form_url`, `description`, `has_phi`) and a raw Forms passthrough (`raw_response` with positional fields).

#### Scenario: Structured input
- **WHEN** the request body contains `form_url` and `has_phi` at the top level
- **THEN** the endpoint SHALL use those values directly

#### Scenario: Raw passthrough input
- **WHEN** the request body contains `raw_response` from a Forms webhook
- **THEN** the endpoint SHALL extract `form_url` from the first non-metadata field, `description` from the second, and `has_phi` from the third

### Requirement: Validate required fields
The endpoint SHALL require `form_url` and `has_phi`, and extract a valid form ID from the URL.

#### Scenario: Missing form_url
- **WHEN** `form_url` is not provided or empty
- **THEN** the endpoint SHALL return HTTP `400`

#### Scenario: Invalid form URL
- **WHEN** `form_id` cannot be extracted from the URL
- **THEN** the endpoint SHALL return HTTP `400`

#### Scenario: Missing has_phi
- **WHEN** `has_phi` is not provided
- **THEN** the endpoint SHALL return HTTP `400`

### Requirement: Normalize has_phi to boolean
The endpoint SHALL accept boolean, string (`"true"`, `"yes"`, `"1"`), and other types for `has_phi` and normalize to a Python boolean.

#### Scenario: String "Yes" input
- **WHEN** `has_phi` is the string `"Yes"`
- **THEN** it SHALL be normalized to `true`

#### Scenario: Boolean false input
- **WHEN** `has_phi` is boolean `false`
- **THEN** it SHALL remain `false`

### Requirement: Create form registry entry
On successful registration, the endpoint SHALL create a `FormConfig` entry with `form_id`, `form_name` (from description, max 50 chars), `target_table` (slugified form_name), initial empty `fields` array, and status based on PHI flag.

#### Scenario: Form with PHI
- **WHEN** `has_phi` is `true`
- **THEN** the form status SHALL be `"pending_review"`

#### Scenario: Form without PHI
- **WHEN** `has_phi` is `false`
- **THEN** the form status SHALL be `"active"`

### Requirement: Handle duplicate registration
The endpoint SHALL return success (not error) when a form is already registered.

#### Scenario: Already registered form
- **WHEN** `form_id` already exists in the registry
- **THEN** the endpoint SHALL return HTTP `200` with status `"already_registered"` and existing metadata

### Requirement: Generate flow definition
On successful registration, the endpoint SHALL attempt to generate a Power Automate flow definition and include it in the response as `flow_create_body`.

#### Scenario: Flow definition generated
- **WHEN** registration succeeds and flow generation succeeds
- **THEN** the response SHALL include `flow_create_body` with display name `"Forms to Fabric - {form_name}"` and state `"Started"`

### Requirement: Return structured response
The endpoint SHALL return a JSON response with form metadata.

#### Scenario: Successful registration
- **WHEN** registration completes
- **THEN** the endpoint SHALL return HTTP `200` with `form_id`, `form_name`, `target_table`, `status`, `field_count`, `generate_flow_url`, and optionally `flow_create_body`
