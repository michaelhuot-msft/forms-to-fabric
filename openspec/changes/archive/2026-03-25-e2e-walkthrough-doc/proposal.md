## Why

The clinician-guide.md and other docs contain screenshot placeholders (e.g., `[Screenshot: Forms home page]`) but no actual images. The existing repo screenshots are manual captures scattered in the root directory with inconsistent naming. There is no automated way to keep documentation screenshots current as the UI evolves. A Playwright-driven E2E walkthrough using Edge will produce a repeatable, maintainable screenshot pipeline that documents the full user journey from form creation through Power BI reporting.

## What Changes

- Add a Playwright test suite (TypeScript/Edge) that walks through the complete Forms-to-Fabric pipeline and captures screenshots at each step — covering both the clinician journey and the admin approval flow
- Generate a new `docs/e2e-walkthrough.md` document assembling those screenshots into a narrated end-to-end guide
- Store generated screenshots in `docs/images/e2e/` with descriptive filenames
- Add npm scripts and configuration for running the Playwright capture pipeline
- Replace placeholder text in `docs/clinician-guide.md` with actual screenshot references where applicable

## Capabilities

### New Capabilities
- `playwright-screenshot-pipeline`: Playwright configuration, Edge browser setup, and screenshot capture scripts that walk through the Forms-to-Fabric flow
- `e2e-walkthrough-document`: Markdown document assembling captured screenshots into a narrated step-by-step guide covering form creation, response submission, data processing, and Power BI visualization

### Modified Capabilities
<!-- No existing spec-level requirements are changing -->

## Impact

- **New files**: `playwright.config.ts`, `e2e/` test directory, `docs/e2e-walkthrough.md`, `docs/images/e2e/*.png`
- **New dependencies**: `@playwright/test` (dev dependency), Node.js tooling alongside existing Python stack
- **Modified files**: `docs/clinician-guide.md` (replace screenshot placeholders with real image references)
- **CI consideration**: Playwright runs are optional/manual (not blocking PR CI) since they require live M365 tenant access
- **No impact** on existing Python Azure Functions, Bicep infrastructure, or pytest suite
