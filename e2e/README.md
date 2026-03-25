# E2E Screenshot Pipeline

Automated screenshot capture for Forms-to-Fabric documentation using [Playwright](https://playwright.dev/) and Microsoft Edge.

## Prerequisites

- **Node.js 18+** — [Download](https://nodejs.org/)
- **Microsoft Edge** — installed on your machine (Playwright uses the `msedge` channel)
- **M365 tenant access** — you need credentials for tenant `6dd0fc78-2408-43d6-a255-4383fbda3f76`

## Setup

```bash
cd e2e
npm install
```

## Authentication

Before running captures, authenticate with M365. This opens Edge for manual login (MFA supported):

```bash
npm run auth-setup
```

This saves your session to `.auth/state.json` (git-ignored). Re-run if your session expires.

## Capture Screenshots

Run the full pipeline:

```bash
npm run capture
```

Screenshots are saved to `docs/images/e2e/` with descriptive filenames:

| File | Step |
|------|------|
| `01-forms-home.png` | Microsoft Forms landing page |
| `02-create-form-title.png` | Form builder — title and description |
| `02-create-form-question.png` | Form builder — adding a question |
| `03-share-form.png` | Share dialog with form link |
| `04-register-form-blank.png` | Registration form (empty) |
| `04-register-form-filled.png` | Registration form (filled) |
| `04-register-form-confirmation.png` | Registration confirmation |
| `05-registration-flow.png` | Registration flow run history |
| `06-admin-approval-flows.png` | Admin flow list |
| `06-admin-approval-activate.png` | Admin activation endpoint |
| `07-submit-response-blank.png` | Form responder view (empty) |
| `07-submit-response-filled.png` | Form responder view (filled) |
| `07-submit-response-confirmation.png` | Submission confirmation |
| `08-data-flow.png` | Data processing flow run |
| `09-lakehouse-overview.png` | Fabric Lakehouse overview |
| `09-lakehouse-raw-table.png` | Raw data table |
| `09-lakehouse-curated-table.png` | De-identified curated table |

## Run a Single Step

```bash
npx playwright test captures/01-forms-home.spec.ts
```

## Run in Headed Mode (Visible Browser)

```bash
npm run capture:headed
```

## Troubleshooting

**"Auth state not found"** — Run `npm run auth-setup` first.

**"Auth state expired"** — Re-run `npm run auth-setup` to refresh your session.

**Edge not found** — Ensure Microsoft Edge is installed. Playwright uses the `msedge` channel which requires a local Edge installation.

**M365 pages not loading** — Check your network connection and that you have access to the tenant.
