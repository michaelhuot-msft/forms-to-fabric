## 1. Project Scaffolding

- [x] 1.1 Create `e2e/` directory with `package.json` (name, scripts including `capture` and `auth-setup`)
- [x] 1.2 Add `@playwright/test` and `typescript` as dev dependencies and run `npm install`
- [x] 1.3 Create `e2e/tsconfig.json` with strict TypeScript configuration
- [x] 1.4 Create `e2e/playwright.config.ts` targeting the `msedge` channel with screenshot output to `docs/images/e2e/`
- [x] 1.5 Add `e2e/.auth/` and `e2e/node_modules/` to the project `.gitignore`
- [x] 1.6 Create `docs/images/e2e/` directory with a `.gitkeep` placeholder

## 2. Authentication Setup

- [x] 2.1 Create `e2e/auth-setup.ts` script that opens Edge to the M365 login page (tenant `6dd0fc78-2408-43d6-a255-4383fbda3f76`, user from 1Password → Microsoft vault → "mhuotexternal main user") and waits for manual authentication
- [x] 2.2 Implement storage state persistence — save authenticated session to `e2e/.auth/state.json` after login completes
- [x] 2.3 Add storage state validation in the Playwright config — detect expired/missing state and surface a clear error message

## 3. Screenshot Capture Scripts

- [x] 3.1 Create `e2e/captures/01-forms-home.spec.ts` — navigate to forms.office.com, capture the Forms landing page
- [x] 3.2 Create `e2e/captures/02-create-form.spec.ts` — acting as clinician, create a new form with title/description/questions, capture form builder screenshots
- [x] 3.3 Create `e2e/captures/03-share-form.spec.ts` — open the share dialog, copy the share link (needed for registration), capture screenshot
- [x] 3.4 Create `e2e/captures/04-register-form.spec.ts` — open the self-service registration form, submit the new form's share link + name + PHI flag, capture the 3-question registration form and confirmation
- [x] 3.5 Create `e2e/captures/05-registration-flow.spec.ts` — navigate to Power Automate, capture the registration flow run completing successfully
- [x] 3.6 Create `e2e/captures/06-admin-approval.spec.ts` — capture the admin activating the form (pending_review → active) via the activation endpoint/portal
- [x] 3.7 Create `e2e/captures/07-submit-response.spec.ts` — open the registered form's responder view, fill out and submit a sample response, capture fill experience and confirmation
- [x] 3.8 Create `e2e/captures/08-data-flow.spec.ts` — navigate to Power Automate, capture the per-form data processing flow run completing successfully
- [x] 3.9 Create `e2e/captures/09-lakehouse-data.spec.ts` — navigate to Fabric Lakehouse, capture raw and curated table views showing the ingested data

## 4. Walkthrough Document

- [x] 4.1 Create `docs/e2e-walkthrough.md` with pipeline overview section including a Mermaid flow diagram using the project's standard dual-mode color palette
- [x] 4.2 Write the Form Creation section — clinician creates a new form in Microsoft Forms (`01-forms-home.png`, `02-create-form.png`, `03-share-form.png`)
- [x] 4.3 Write the Self-Service Registration section — clinician registers the form via the registration form (`04-register-form.png`, `05-registration-flow.png`)
- [x] 4.4 Write the Admin Approval section — IT admin reviews and activates the PHI form (`06-admin-approval.png`)
- [x] 4.5 Write the Response Collection section — clinician collects a sample response (`07-submit-response.png`)
- [x] 4.6 Write the Data Processing section — data flows through to Fabric (`08-data-flow.png`, `09-lakehouse-data.png`)
- [x] 4.7 Ensure all image references include descriptive alt text for accessibility

## 5. Clinician Guide Updates

- [x] 5.1 Audit `docs/clinician-guide.md` for all `[Screenshot: ...]` placeholder instances
- [x] 5.2 Replace each placeholder with the corresponding markdown image reference from `docs/images/e2e/`
- [x] 5.3 Verify no broken image references remain in the clinician guide

## 6. Documentation and Cleanup

- [x] 6.1 Add a `README.md` inside `e2e/` explaining prerequisites (Edge installed, M365 tenant access), setup steps, and how to run the pipeline
- [x] 6.2 Update the project root `README.md` to mention the E2E walkthrough and link to `docs/e2e-walkthrough.md`
- [x] 6.3 Verify the complete pipeline runs end-to-end: auth setup → screenshot capture → markdown document renders correctly with all images
