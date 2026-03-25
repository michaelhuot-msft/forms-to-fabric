# De-Identification

> Capability: `de-identification`
> Source: `src/functions/deid.py`

## Requirements

### Requirement: Return raw and de-identified record pairs
The `apply_deid` function SHALL accept a list of answers and field configurations, and return a tuple of `(raw_records, deid_records)` where each record is `{"field_name": str, "value": str}`.

#### Scenario: Basic invocation
- **WHEN** `apply_deid(answers, field_configs)` is called
- **THEN** it SHALL return `(raw_records, deid_records)` with one entry per answer in each list

### Requirement: Hash method uses SHA-256
When `deid_method` is `"hash"`, the value SHALL be transformed using `hashlib.sha256(value.encode("utf-8")).hexdigest()`, producing a deterministic 64-character hex string.

#### Scenario: Hash a value
- **WHEN** a field has `deid_method="hash"` and value `"John"`
- **THEN** the de-identified value SHALL be the SHA-256 hex digest of `"John"`

#### Scenario: Hash is deterministic
- **WHEN** the same value is hashed twice
- **THEN** both outputs SHALL be identical

### Requirement: Redact method replaces with placeholder
When `deid_method` is `"redact"`, the value SHALL be replaced with the fixed string `"[REDACTED]"`.

#### Scenario: Redact a value
- **WHEN** a field has `deid_method="redact"` and any value
- **THEN** the de-identified value SHALL be `"[REDACTED]"`

### Requirement: Generalize method reduces precision
When `deid_method` is `"generalize"`, the transformation SHALL depend on `field_type`.

#### Scenario: Generalize a date
- **WHEN** `field_type="date"` and value matches `(\d{4})-(\d{2})`
- **THEN** the output SHALL be year-month only (e.g., `"2024-01-15"` → `"2024-01"`)

#### Scenario: Generalize a date that does not match pattern
- **WHEN** `field_type="date"` and value does not match the regex
- **THEN** the original value SHALL be returned unchanged

#### Scenario: Generalize an age
- **WHEN** `field_type="age"` and value is a parseable integer
- **THEN** the output SHALL be a decade range (e.g., `35` → `"30-39"`)

#### Scenario: Generalize an age that cannot be parsed
- **WHEN** `field_type="age"` and value cannot be parsed as integer
- **THEN** the original value SHALL be returned unchanged

#### Scenario: Generalize with unknown field_type
- **WHEN** `field_type` is not `"date"` or `"age"` (or is null)
- **THEN** the output SHALL be `"[GENERALIZED]"`

### Requirement: Non-PHI fields pass through unchanged
When a field has `contains_phi=false` or no `deid_method`, the value SHALL pass through to the de-identified record unchanged.

#### Scenario: Non-PHI field
- **WHEN** a field has `contains_phi=false`
- **THEN** the de-identified value SHALL equal the original value

### Requirement: Raw records always contain original values
Regardless of de-identification method, the raw record for every field SHALL contain the original unmodified value.

#### Scenario: Raw record preservation
- **WHEN** any field is processed
- **THEN** the raw record SHALL contain `{"field_name": field_name, "value": original_value}`
