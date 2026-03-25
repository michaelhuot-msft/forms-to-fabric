## ADDED Requirements

### Requirement: E2E walkthrough markdown document
The system SHALL include a markdown document at `docs/e2e-walkthrough.md` that narrates the complete Forms-to-Fabric pipeline with embedded screenshots captured by Playwright.

#### Scenario: Document exists and is well-structured
- **WHEN** a reader opens `docs/e2e-walkthrough.md`
- **THEN** it SHALL contain titled sections for each phase of the pipeline: form creation, response submission, data processing, and data visualization

#### Scenario: Screenshots are embedded with alt text
- **WHEN** the document references a screenshot
- **THEN** it SHALL use standard markdown image syntax with descriptive alt text (e.g., `![Forms home page showing the new form button](images/e2e/01-forms-home.png)`)

### Requirement: Document covers the complete clinician journey
The walkthrough document SHALL cover every step a clinician follows from creating a form to viewing results, and every step an admin follows to approve and activate forms.

#### Scenario: Form creation section
- **WHEN** a reader views the form creation section
- **THEN** it SHALL include screenshots and narration for: navigating to Forms, creating a new form, adding a title and description, adding questions with different types, configuring settings, and copying the share link

#### Scenario: Self-service registration section
- **WHEN** a reader views the self-service registration section
- **THEN** it SHALL include screenshots and narration for: opening the registration form, submitting the new form's share link along with a name and PHI designation, and the registration flow executing successfully in Power Automate

#### Scenario: Admin approval section
- **WHEN** a reader views the admin approval section
- **THEN** it SHALL include screenshots and narration for: reviewing a pending form registration, activating the form via the admin endpoint, and confirming the form status transitions to active

#### Scenario: Response collection section
- **WHEN** a reader views the response collection section
- **THEN** it SHALL include screenshots and narration for: opening the registered form's responder view, filling out a sample response, and confirming submission

#### Scenario: Data processing section
- **WHEN** a reader views the data processing section
- **THEN** it SHALL include screenshots and narration for: the per-form data flow triggering in Power Automate, and the ingested data appearing in the Fabric Lakehouse raw and curated tables

### Requirement: Clinician guide screenshot replacement
The existing `docs/clinician-guide.md` SHALL have its placeholder text replaced with references to actual screenshots from the E2E pipeline.

#### Scenario: Placeholder replacement
- **WHEN** `docs/clinician-guide.md` contains placeholder text matching `[Screenshot: <description>]`
- **THEN** each placeholder SHALL be replaced with a markdown image reference pointing to the corresponding screenshot in `docs/images/e2e/`

#### Scenario: No broken image references
- **WHEN** the clinician guide references a screenshot file
- **THEN** that file SHALL exist at the referenced path in the repository

### Requirement: Document follows project documentation standards
The walkthrough document SHALL follow the project's existing documentation conventions.

#### Scenario: Mermaid diagram for pipeline overview
- **WHEN** the document includes an architecture or flow overview
- **THEN** it SHALL use Mermaid syntax with the project's standard dual-mode color palette (primary, success, warning, danger, info, neutral classes)

#### Scenario: Accessibility compliance
- **WHEN** the document includes images
- **THEN** every image SHALL have descriptive alt text that conveys the same information as the screenshot for screen reader users
