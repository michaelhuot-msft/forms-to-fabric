## ADDED Requirements

### Requirement: Playwright project configuration
The system SHALL include a Playwright configuration file (`e2e/playwright.config.ts`) that targets the Microsoft Edge browser channel and outputs screenshots to `docs/images/e2e/`.

#### Scenario: Default browser is Edge
- **WHEN** the Playwright pipeline runs without browser override
- **THEN** it SHALL launch Microsoft Edge via the `msedge` channel

#### Scenario: Screenshot output directory
- **WHEN** a screenshot is captured during a pipeline run
- **THEN** it SHALL be saved to `docs/images/e2e/` with a descriptive filename prefixed by a zero-padded step number (e.g., `01-forms-home.png`)

### Requirement: Authentication state management
The system SHALL provide an auth helper script (`e2e/auth-setup.ts`) that opens an Edge browser window for manual M365 login and persists the authenticated session to a local storage state file.

#### Scenario: First-time authentication
- **WHEN** a user runs the auth setup script and no storage state file exists
- **THEN** the script SHALL open Edge to the M365 login page for tenant `6dd0fc78-2408-43d6-a255-4383fbda3f76` and wait for the user to complete authentication
- **THEN** the script SHALL save the browser storage state to `e2e/.auth/state.json`

#### Scenario: Storage state is git-ignored
- **WHEN** the auth state file is saved
- **THEN** the path `e2e/.auth/` SHALL be listed in `.gitignore` to prevent credential leakage

#### Scenario: Expired authentication
- **WHEN** the pipeline runs with an expired or invalid storage state
- **THEN** the pipeline SHALL exit with a clear error message instructing the user to re-run the auth setup script

### Requirement: Screenshot capture for each pipeline step
The system SHALL capture a full-page or element-targeted screenshot at each major step of the Forms-to-Fabric pipeline flow.

#### Scenario: Forms home page
- **WHEN** the pipeline navigates to forms.office.com
- **THEN** it SHALL capture a screenshot showing the Forms landing page

#### Scenario: Form creation
- **WHEN** the pipeline creates a new Microsoft Form acting as a clinician
- **THEN** it SHALL capture screenshots of the form builder showing the form title, description, and question fields being added (this form will be used for the registration step)

#### Scenario: Form sharing
- **WHEN** the pipeline opens the form share dialog to copy the share link
- **THEN** it SHALL capture a screenshot showing the share link (this link is needed for the registration form)

#### Scenario: Self-service form registration
- **WHEN** the pipeline opens the self-service registration form and submits the newly created form's share link, name, and PHI designation
- **THEN** it SHALL capture screenshots of filling out the 3-question registration form and the submission confirmation

#### Scenario: Registration flow execution
- **WHEN** the registration flow triggers in Power Automate after form registration
- **THEN** it SHALL capture a screenshot showing the registration flow run completing successfully

#### Scenario: Admin approval flow
- **WHEN** the pipeline navigates to the activate-form admin endpoint or portal to approve a PHI form
- **THEN** it SHALL capture a screenshot showing the admin approval step that transitions a form from pending_review to active status

#### Scenario: Form response submission
- **WHEN** the pipeline opens the newly registered form's responder view and submits a sample response
- **THEN** it SHALL capture screenshots of the form fill experience and the submission confirmation

#### Scenario: Per-form data flow trigger
- **WHEN** the per-form data processing flow triggers in Power Automate after a response is submitted
- **THEN** it SHALL capture a screenshot showing a successful data flow run

#### Scenario: Fabric Lakehouse data
- **WHEN** the pipeline navigates to the Fabric Lakehouse table view
- **THEN** it SHALL capture a screenshot showing the ingested data rows in both raw and curated tables

### Requirement: Pipeline runner script
The system SHALL provide an npm script (`npm run capture` in `e2e/package.json`) that executes the full screenshot pipeline in sequence.

#### Scenario: Full pipeline execution
- **WHEN** a user runs `npm run capture` from the `e2e/` directory
- **THEN** Playwright SHALL execute all capture steps in order, saving screenshots to `docs/images/e2e/`

#### Scenario: Individual step execution
- **WHEN** a user runs `npx playwright test <step-file>` for a single step
- **THEN** only that step's screenshots SHALL be captured

### Requirement: Stable and descriptive screenshot filenames
All generated screenshots SHALL use descriptive, kebab-case filenames with zero-padded step prefixes for natural sort ordering.

#### Scenario: Filename format
- **WHEN** any screenshot is saved
- **THEN** its filename SHALL match the pattern `NN-descriptive-name.png` where NN is a zero-padded step number (e.g., `01-forms-home.png`, `06-lakehouse-raw-table.png`)

#### Scenario: Deterministic output
- **WHEN** the pipeline runs twice against the same environment state
- **THEN** it SHALL produce the same set of filenames, overwriting previous captures
