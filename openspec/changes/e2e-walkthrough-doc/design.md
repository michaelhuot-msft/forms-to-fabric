## Context

The Forms-to-Fabric project documents a clinician-facing pipeline from Microsoft Forms through Azure Functions into a Fabric Lakehouse. Current documentation includes placeholder text like `[Screenshot: Forms home page]` in the clinician guide, and a handful of manually-captured PNGs in the repo root with inconsistent naming. There is no automated way to regenerate screenshots when the UI changes, and no visual E2E walkthrough exists.

The project already has a Python/pytest test suite for unit and integration testing, but no browser automation. Adding Playwright with Edge aligns with the M365 ecosystem (Edge is the default enterprise browser) and provides a maintainable screenshot pipeline.

## Goals / Non-Goals

**Goals:**
- Automate screenshot capture for every major step in the Forms-to-Fabric flow using Playwright + Edge
- Produce a narrated `docs/e2e-walkthrough.md` that assembles screenshots into a complete guide
- Store screenshots in `docs/images/e2e/` with descriptive, stable filenames
- Make the pipeline re-runnable so screenshots stay current as UIs evolve
- Replace placeholder text in `docs/clinician-guide.md` with real image references
- Cover both the clinician flow (form creation → response → data) and the admin flow (form approval via activate-form)

**Non-Goals:**
- Functional E2E testing or assertions (this is a documentation tool, not a test suite)
- Automating Power Automate flow execution (manual trigger, capture results)
- Running Playwright in CI on every PR (requires live M365 tenant credentials)
- Capturing Fabric admin or infrastructure provisioning steps (covered by existing setup guides)

## Decisions

### 1. Playwright over Puppeteer or Selenium

**Choice**: Playwright with `@playwright/test` runner

**Rationale**: Playwright has first-class Edge/Chromium support via the `msedge` channel, built-in screenshot APIs with element-level targeting, and automatic waiting that handles M365's dynamic loading states. The user explicitly requested Playwright + Edge.

**Alternatives considered**:
- Puppeteer — No built-in Edge channel; less robust waiting
- Selenium — Heavier setup, no built-in screenshot diffing, slower execution

### 2. TypeScript over Python for Playwright scripts

**Choice**: TypeScript with `@playwright/test`

**Rationale**: Playwright's TypeScript integration is the most mature and best-documented. The screenshot pipeline is a standalone tooling concern, not part of the Python Azure Functions codebase. Keeping it in TypeScript avoids polluting the Python dependency tree.

### 3. Screenshot storage in `docs/images/e2e/`

**Choice**: Commit generated PNGs to `docs/images/e2e/` with descriptive names

**Rationale**: Screenshots are part of the documentation — they should be versioned alongside the markdown that references them. Storing in a dedicated subdirectory avoids cluttering the root. Filenames use step numbering (e.g., `01-forms-home.png`, `02-create-new-form.png`) for natural ordering.

**Alternatives considered**:
- Git LFS — Adds complexity; PNGs are small (typically <500KB each)
- External hosting — Breaks offline viewing and version tracking

### 4. Manual authentication, not automated login

**Choice**: Use Playwright's `storageState` to persist authenticated sessions

**Rationale**: M365 login involves MFA and conditional access policies that cannot be reliably automated. The workflow is: (1) run a one-time auth helper that opens Edge for manual login, (2) save the browser storage state to a local file (git-ignored), (3) subsequent Playwright runs reuse that state. This avoids storing credentials.

### 5. Standalone npm project in `e2e/` directory

**Choice**: Place Playwright config and scripts in a top-level `e2e/` directory

**Rationale**: Keeps browser automation tooling separate from the Python Azure Functions in `src/functions/` and the pytest suite in `tests/`. The `e2e/` directory gets its own `package.json` and `tsconfig.json` without affecting the rest of the project.

## Risks / Trade-offs

- **M365 UI changes** → Screenshots break when Microsoft updates Forms/Fabric UI. Mitigation: re-run the pipeline periodically; use element selectors that target stable attributes.
- **Auth token expiry** → Saved storage state expires. Mitigation: auth helper script detects stale state and prompts re-login before capture run.
- **Tenant-specific content** → Screenshots show real tenant data. Mitigation: use a dedicated test tenant or sanitize screenshots (crop/blur sensitive areas).
- **Large binary diffs** → Regenerated PNGs create large git diffs. Mitigation: only commit screenshots when meaningful UI changes occur, not on every pipeline run.
- **Edge channel availability** → Playwright's `msedge` channel requires Edge installed on the machine. Mitigation: document prerequisite; fall back to Chromium in CI if needed.

## Resolved Questions

- **Tenant**: `6dd0fc78-2408-43d6-a255-4383fbda3f76` (mngenvmcap732807.onmicrosoft.com)
- **User**: `michaelhuot@mngenvmcap732807.onmicrosoft.com` (credentials in 1Password → Microsoft vault → "mhuotexternal main user")
- **Admin flow**: Yes — the walkthrough covers both the clinician journey AND the admin approval flow (activate-form)
- **Visualization**: Lakehouse table view only (no Power BI dashboard captures)
