# Form Processing

> Capability: `form-processing`
> Route: `POST /api/process-response`
> Source: `src/functions/process_response.py`

## Requirements

### Requirement: Validate request payload
The endpoint SHALL validate the incoming HTTP request body against the `FormResponse` Pydantic model. It SHALL return `400` if the body is not valid JSON, if Pydantic validation fails, or if the answers array is empty after extraction.

#### Scenario: Invalid JSON body
- **WHEN** the request body is not valid JSON
- **THEN** the endpoint SHALL return HTTP `400` with message `"Invalid JSON in request body"`

#### Scenario: Pydantic validation failure
- **WHEN** the request body fails Pydantic validation
- **THEN** the endpoint SHALL return HTTP `400` with message `"Payload validation failed: {count} error(s) — {details}"`

#### Scenario: Empty answers after extraction
- **WHEN** the answers array is empty after raw_response extraction
- **THEN** the endpoint SHALL return HTTP `400` with message `"answers array must not be empty"`

### Requirement: Extract answers from raw_response
When `raw_response` is provided and `answers` is empty, the endpoint SHALL extract metadata fields (`responder`, `submitDate`, `responseId`) and build the answers array from all remaining non-metadata fields.

#### Scenario: Raw response passthrough
- **WHEN** `raw_response` is provided and `answers` is empty
- **THEN** the endpoint SHALL extract `responder` → `respondent_email`, `submitDate` → `submitted_at`, `responseId` → `response_id`
- **AND** build answers from all fields not in `{"responder", "submitDate", "responseId", "@odata.context", "@odata.etag"}` or starting with `@`

### Requirement: Lookup form in registry
The endpoint SHALL look up the `form_id` in the form registry and reject unknown forms.

#### Scenario: Unknown form_id
- **WHEN** `form_id` is not found in the registry
- **THEN** the endpoint SHALL return HTTP `404` with message `"Unknown form_id: {form_id}"`

### Requirement: Reject non-active forms
The endpoint SHALL reject submissions for forms that are not in `active` status.

#### Scenario: Form not active
- **WHEN** the form status is not `"active"`
- **THEN** the endpoint SHALL return HTTP `403` with message `"Form '{form_id}' is not active (status: {status})"`

### Requirement: Write raw data to OneLake
The endpoint SHALL always write the unmodified response data to the OneLake raw layer table (`{target_table}_raw`).

#### Scenario: Raw layer write
- **WHEN** a valid submission is processed
- **THEN** the raw response data (all fields, unmodified) SHALL be written to the raw layer with metadata: `response_id`, `form_id`, `submitted_at`, `respondent_email`

### Requirement: Apply de-identification and write curated data
The endpoint SHALL apply de-identification rules per field configuration and write the result to the curated layer, but only if the form has PHI fields.

#### Scenario: Form with PHI fields
- **WHEN** a form has fields with `contains_phi=true`
- **THEN** the de-identified data SHALL be written to the curated layer table (`{target_table}_curated`)

#### Scenario: Form without PHI fields
- **WHEN** no fields have `contains_phi=true`
- **THEN** the curated layer write SHALL be skipped (curated_path is null in response)

### Requirement: Quarantine unregistered fields
Fields not registered in the form configuration SHALL be included in the raw layer but excluded from the curated layer.

#### Scenario: Unregistered field submitted
- **WHEN** an answer has a `question_id` not found in the form's field configuration
- **THEN** the field SHALL be included in the raw layer write
- **AND** excluded from the curated layer write
- **AND** a warning SHALL be logged: `"Unregistered field '{question_id}' in form '{form_id}' — included in raw layer, excluded from curated"`

### Requirement: Handle OneLake errors gracefully
The endpoint SHALL return appropriate error codes for infrastructure failures.

#### Scenario: OneLake write failure
- **WHEN** writing to OneLake raises a `RuntimeError`
- **THEN** the endpoint SHALL return HTTP `502` with the error message

#### Scenario: Fabric capacity unavailable
- **WHEN** a `FabricCapacityError` is raised
- **THEN** the endpoint SHALL return HTTP `503` with the error message

### Requirement: Return structured response
The endpoint SHALL return a JSON response indicating success or failure.

#### Scenario: Successful processing
- **WHEN** processing completes without error
- **THEN** the endpoint SHALL return HTTP `200` with `{"status": "success", "response_id": "...", "form_id": "...", "raw_path": "...", "curated_path": "..."}`
