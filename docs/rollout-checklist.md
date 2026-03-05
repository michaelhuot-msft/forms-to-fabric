# Forms-to-Fabric Pipeline — Department Onboarding Checklist

This checklist is a template for onboarding a new department to the Forms-to-Fabric pipeline. Copy this checklist for each department and track completion.

## Department Information

| Field | Value |
|-------|-------|
| Department Name | _________________ |
| Department Liaison | _________________ |
| Liaison Email | _________________ |
| Target Go-Live Date | _________________ |
| Number of Forms | _________________ |
| Estimated Responses/Week | _________________ |

## Pre-Onboarding

- [ ] Department liaison identified and confirmed
- [ ] Kickoff meeting held with department liaison
- [ ] Department requirements gathered (number of forms, data types, reporting needs)
- [ ] PHI/sensitivity assessment completed for each planned form
- [ ] Timeline agreed upon with department

## Form Setup

- [ ] Forms created in Microsoft Forms (by clinician or IT)
- [ ] Forms tested with sample data
- [ ] Form IDs collected and documented
- [ ] Field-level sensitivity classification completed
- [ ] De-identification rules configured and reviewed with privacy officer
- [ ] Form registration entries added to `config/form-registry.json`
- [ ] Configuration deployed (`azd deploy`)

## Infrastructure & Access

- [ ] Fabric workspace access granted to department (appropriate roles)
- [ ] Power Automate flow created for each form
- [ ] Power Automate flow tested with sample submission
- [ ] Power BI dashboard created for department
- [ ] Dashboard shared with appropriate users (Viewer role)
- [ ] Row-level security configured (if multi-department workspace)

## Testing

- [ ] End-to-end test completed (form → Lakehouse → dashboard)
- [ ] Raw layer data verified (all fields present)
- [ ] Curated layer data verified (de-identification applied correctly)
- [ ] Dashboard displays data correctly
- [ ] Error handling tested (submit malformed data, verify error notification)
- [ ] De-identification audit passed (no PHI in curated layer)

## Training

- [ ] Training session scheduled
- [ ] Training session completed
- [ ] Training materials shared (clinician guide, FAQ)
- [ ] Support contact information provided
- [ ] Department knows how to report issues

## Go-Live

- [ ] Go-live date confirmed with department
- [ ] IT on-call support arranged for go-live day
- [ ] Go-live announcement sent to department
- [ ] Forms activated for real data collection

## Post-Launch

- [ ] Post-launch check-in completed (1 week after go-live)
- [ ] Any issues from first week resolved
- [ ] Feedback collected from clinicians (2 weeks after go-live)
- [ ] Feedback reviewed and action items documented
- [ ] Department signed off on successful onboarding
- [ ] Lessons learned documented for future onboarding

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Department Liaison | | | |
| IT Admin | | | |
| Privacy Officer | | | |
| Project Manager | | | |

---

*Template version: 1.0*
*Last updated: 2025-07-15*
*See [setup-guide.md](setup-guide.md) for technical deployment steps and [admin-guide.md](admin-guide.md) for configuration details.*
