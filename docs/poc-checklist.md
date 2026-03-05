# POC Readiness Checklist

> **Purpose:** A reusable checklist for building proof-of-concept / reference implementations. Derived from lessons learned building the Forms to Fabric pipeline.
>
> **How to use:** Copy this file into your new project repo and work through each section. Check items off as you complete them. Delete sections that don't apply.

---

## Phase 1: Discovery & Planning

### Requirements Capture
- [ ] Stakeholder interviews completed — document who was consulted
- [ ] Core problem statement written (1–2 sentences)
- [ ] User personas identified (who uses this and what's their skill level?)
- [ ] Data sensitivity assessed (PHI, PII, confidential, public?)
- [ ] Compliance requirements identified (HIPAA, SOC2, GDPR, none?)
- [ ] Integration points listed (what systems does this connect to?)
- [ ] Scale expectations defined (start small, or known volume?)

### Decisions Log
- [ ] Create a `docs/decisions.md` file from day one
- [ ] Record every significant decision with:
  - What was decided
  - Why (context/rationale)
  - What alternatives were considered
  - How to change it later
- [ ] Have the customer validate decisions before implementation

### Success Criteria
- [ ] Define measurable success criteria (not just "it works")
- [ ] Agree on what "done" looks like with stakeholders
- [ ] Define go/no-go criteria for any pilot phase

---

## Phase 2: Documentation First

> Write user-facing docs BEFORE code. This validates the experience with stakeholders and catches misunderstandings early.

### User Documentation
- [ ] End-user guide written in plain language (no jargon)
- [ ] FAQ covering the top 10 questions users will ask
- [ ] Training materials outline (slides, video script, or workshop plan)

### Technical Documentation
- [ ] Architecture document with diagram
- [ ] Setup/deployment guide (step-by-step, copy-paste commands)
- [ ] Admin/operations guide
- [ ] API documentation (if applicable)

### Stakeholder Review
- [ ] User docs reviewed by at least 1 representative end-user
- [ ] Architecture doc reviewed by IT/security stakeholder
- [ ] All docs free of client-identifying information (if repo will be shared)

---

## Phase 3: Implementation

### Repository Setup
- [ ] `.gitignore` configured (no secrets, no IDE files, no build artifacts)
- [ ] `README.md` with project overview, quick start, and project structure
- [ ] `CONTRIBUTING.md` with development guidelines
- [ ] `LICENSE` file (MIT, Apache 2.0, or as required)
- [ ] `DISCLAIMER.md` stating POC/reference status, no support, AS-IS
- [ ] CI/CD pipeline (lint + test + deploy) — even for a POC
- [ ] Infrastructure as Code (Bicep, Terraform, ARM — not manual portal clicks)

### Code Quality
- [ ] Linter configured and passing (ruff, eslint, etc.)
- [ ] Formatter configured and passing (ruff format, prettier, etc.)
- [ ] Type hints / type checking where language supports it
- [ ] Unit tests for core logic (aim for >70% coverage on business logic)
- [ ] Integration tests for critical paths
- [ ] All tests passing in CI before every merge

### Security
- [ ] No secrets in code (use Key Vault, env vars, or managed identity)
- [ ] No hardcoded credentials, connection strings, or API keys
- [ ] No real client/customer data in test fixtures
- [ ] Authentication uses managed identity or federated credentials where possible
- [ ] HTTPS enforced on all endpoints
- [ ] Sensitive data encrypted at rest and in transit

### Atomic Commits
- [ ] Each commit is one logical change (not a giant "update everything" commit)
- [ ] Commit messages describe what changed and why
- [ ] Push after each commit — keep the remote up to date
- [ ] Documentation updated in the same commit as the code it describes

---

## Phase 4: Admin Burden Assessment

> Assess the operational overhead before handing off. A POC that's too expensive to operate won't be adopted.

### Touchpoint Inventory
- [ ] List every manual step required to onboard a new user/entity
- [ ] List every recurring maintenance task (daily, weekly, quarterly)
- [ ] List every troubleshooting scenario and estimated diagnosis time
- [ ] Estimate total admin hours per year at expected scale

### Automation
- [ ] Identify which touchpoints can be automated
- [ ] Prioritize by: risk (P0) > time savings (P1) > convenience (P2)
- [ ] Implement at least the P0 automations before handoff
- [ ] Document remaining manual steps clearly in the admin guide

### Self-Service
- [ ] Can end-users do the most common operation without IT help?
- [ ] If not, what's the simplest self-service path? (form, CLI, API)
- [ ] Document the fallback manual path (v2) alongside any self-service (v3)

---

## Phase 5: Public / Handoff Readiness

### Client Anonymity
- [ ] No client name, project codename, or identifying information in code
- [ ] No real email addresses, domains, or person names (use contoso.com, placeholders)
- [ ] No internal URLs, Jira/ADO ticket numbers, or wiki links
- [ ] Search for client name across entire repo: `grep -ri "client-name" .`

### Support Scope
- [ ] DISCLAIMER.md clearly states: not supported, AS-IS, no SLAs
- [ ] README.md has disclaimer note (top) and full section (bottom)
- [ ] All docs use "your organization" not "our team"
- [ ] No SLA-like language ("within 1-2 business days", "guaranteed uptime")
- [ ] Contact info is clearly marked as template placeholders
- [ ] Pilot program targets framed as "suggested" not "committed"

### Classification Headers
- [ ] No "Classification: Internal" or "Confidential" markers in docs
- [ ] No "Private — All rights reserved" in LICENSE or README

### Final Verification
- [ ] `grep -ri "classification.*internal" docs/` returns nothing
- [ ] `grep -ri "private.*all rights" .` returns nothing
- [ ] `grep -ri "<client-name>" .` returns nothing
- [ ] All tests passing
- [ ] Lint and format passing
- [ ] CI pipeline green (test + lint jobs)
- [ ] Every commit pushed to remote
- [ ] README accurately describes the current state of the project

---

## Phase 6: Pilot (If Applicable)

- [ ] Pilot program plan written with: scope, participants, timeline, metrics
- [ ] Success metrics are measurable and have defined targets
- [ ] Go/no-go criteria documented (with "conditional go" middle path)
- [ ] Feedback collection mechanism set up (form, survey, check-ins)
- [ ] Risk mitigation plan for top 5 risks
- [ ] Communication plan for all stakeholders
- [ ] Rollout checklist template for department-by-department onboarding

---

## Lessons Learned Template

After the POC is complete, fill in:

### What Worked
| Lesson | Detail |
|--------|--------|
| | |

### What Could Be Improved
| Area | Limitation | Potential Fix |
|------|-----------|---------------|
| | | |

### Design Principles That Emerged
1. 
2. 
3. 

---

*This checklist was derived from the [Forms to Fabric](https://github.com/michaelhuot-msft/forms-to-fabric) POC project. See `docs/decisions.md` and `docs/automation-gaps.md` in that repo for the full story.*
