# E2E Screenshot Gallery

> All screenshots captured automatically with Playwright + Microsoft Edge on 2026-03-25.
> For the full narrated walkthrough, see [e2e-walkthrough.md](e2e-walkthrough.md).

---

## 1. Forms Home

![Microsoft Forms home page](images/e2e/01-forms-home.png)

---

## 2. Create a New Form

### Form Title

![Form builder with title "Patient Satisfaction Survey"](images/e2e/02-create-form-title.png)

### Add a Choice Question

![Form builder showing a choice question](images/e2e/02-create-form-question.png)

---

## 3. Share Form

![Collect responses dialog with shareable link](images/e2e/03-share-form.png)

---

## 4. Register Form for Analytics

### Blank Registration Form

![Registration form ready to be filled out](images/e2e/04-register-form-blank.png)

### Filled Registration Form

![Registration form filled with form link, name, and "No" selected for PHI](images/e2e/04-register-form-filled.png)

### Submission Confirmation

![Registration form confirmation — form registered successfully](images/e2e/04-register-form-confirmation.png)

---

## 5. Registration Flow (Power Automate)

![Power Automate My Flows page](images/e2e/05-registration-flow.png)

---

## 6. Admin Approval (Skipped for Non-PHI)

### Flow List

![Power Automate flows list](images/e2e/06-admin-approval-flows.png)

### Azure Portal

![Azure portal home](images/e2e/06-admin-approval-activate.png)

---

## 7. Submit a Response

### Blank Form

![Patient Satisfaction Survey in responder preview view](images/e2e/07-submit-response-blank.png)

### Filled Form

![Survey with Option 1 selected](images/e2e/07-submit-response-filled.png)

### Confirmation

![Response submitted confirmation page](images/e2e/07-submit-response-confirmation.png)

---

## 8. Data Flow (Power Automate)

![Per-form data flow run](images/e2e/08-data-flow.png)

---

## 9. Fabric Lakehouse

### Workspace Overview

![Fabric workspace showing forms_lakehouse](images/e2e/09-lakehouse-overview.png)

### Lakehouse Explorer

![Lakehouse explorer with Tables and Files tree](images/e2e/09-lakehouse-raw-table.png)

### Lakehouse Tables (Empty — Awaiting Data)

![Lakehouse explorer view — tables will populate when data flows](images/e2e/09-lakehouse-curated-table.png)
