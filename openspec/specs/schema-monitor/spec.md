# Schema Monitor

> Capability: `schema-monitor`
> Trigger: Timer — `0 0 */6 * * *` (every 6 hours)
> Source: `src/functions/monitor_schema.py`

## Requirements

### Requirement: Check all registered forms on schedule
The schema monitor SHALL iterate all forms in the registry every 6 hours and compare their registered field configuration against the live form schema from Microsoft Graph API.

#### Scenario: Timer fires
- **WHEN** the timer trigger fires
- **THEN** the monitor SHALL call `check_all_forms()` and process all registered forms

### Requirement: Detect added questions
The monitor SHALL detect questions that exist in the live form but not in the registry.

#### Scenario: New question added to form
- **WHEN** a question ID exists in the live Graph response but not in the registry fields
- **THEN** a `SchemaChange` with `change_type="added"` SHALL be reported with the question ID and title

### Requirement: Detect removed questions
The monitor SHALL detect questions that exist in the registry but not in the live form.

#### Scenario: Question removed from form
- **WHEN** a question ID exists in the registry but not in the live Graph response
- **THEN** a `SchemaChange` with `change_type="removed"` SHALL be reported

### Requirement: Detect renamed questions
The monitor SHALL detect questions whose title has changed between registry and live form.

#### Scenario: Question title changed
- **WHEN** a question ID exists in both registry and live, but the title differs
- **THEN** a `SchemaChange` with `change_type="renamed"` SHALL be reported with old and new values

### Requirement: Handle deleted forms
The monitor SHALL handle forms that no longer exist in Microsoft Forms.

#### Scenario: Form deleted from Microsoft Forms
- **WHEN** the Graph API returns `FormNotFoundError`
- **THEN** a `SchemaChange` with `change_type="removed"`, `question_id="*"`, and `old_value="entire form deleted"` SHALL be reported

### Requirement: Continue on errors
The monitor SHALL not abort when individual form checks fail.

#### Scenario: Access denied for one form
- **WHEN** the Graph API returns `FormAccessDeniedError` for a form
- **THEN** the monitor SHALL log the error, skip that form, and continue with remaining forms

### Requirement: Log and alert on changes
When schema changes are detected, the monitor SHALL log warnings with change details and optionally send email alerts.

#### Scenario: Changes detected
- **WHEN** one or more forms have schema changes
- **THEN** a warning SHALL be logged: `"{count} form(s) have schema changes."`
- **AND** `send_alert()` SHALL be called with the changed reports

#### Scenario: No changes detected
- **WHEN** no forms have schema changes
- **THEN** an info message SHALL be logged: `"No schema changes detected."`
