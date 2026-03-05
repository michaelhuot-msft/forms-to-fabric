"""Azure Function App entry point (v2 programming model).

Registers the HTTP-triggered function that receives Microsoft Forms
responses from Power Automate and writes them to Microsoft Fabric OneLake,
and a timer-triggered function that monitors form schemas for changes.
"""

import logging

import azure.functions as func

from process_response.handler import handle_form_response

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)
logger = logging.getLogger(__name__)


@app.route(route="process-response", methods=["POST"])
def process_response(req: func.HttpRequest) -> func.HttpResponse:
    """HTTP trigger that accepts a form response payload from Power Automate."""
    return handle_form_response(req)


@app.timer_trigger(schedule="0 0 */6 * * *", arg_name="timer", run_on_startup=False)
def monitor_schema(timer: func.TimerRequest) -> None:
    """Check registered forms for schema changes every 6 hours."""
    from monitor_schema.handler import check_all_forms, send_alert

    logger.info("Schema monitor triggered. Checking all registered forms.")
    reports = check_all_forms()
    changed = [r for r in reports if r.has_changes]
    if changed:
        logger.warning("%d form(s) have schema changes.", len(changed))
        send_alert(changed)
    else:
        logger.info("No schema changes detected.")


@app.timer_trigger(schedule="0 0 8 * * *", arg_name="timer", run_on_startup=False)
def audit_rbac(timer: func.TimerRequest) -> None:
    """Daily RBAC audit of Fabric workspace access."""
    from audit_rbac.handler import audit_workspace_access, send_audit_alert

    report = audit_workspace_access()
    send_audit_alert(report)


@app.route(route="generate-flow", methods=["GET"], auth_level=func.AuthLevel.FUNCTION)
def generate_flow(req: func.HttpRequest) -> func.HttpResponse:
    """Generate a Power Automate flow definition for a registered form."""
    from generate_flow.handler import handle_generate_flow

    return handle_generate_flow(req)


@app.route(route="register-form", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def register_form(req: func.HttpRequest) -> func.HttpResponse:
    """Register a new form for pipeline processing."""
    from register_form.handler import handle_register_form

    return handle_register_form(req)


@app.route(route="activate-form", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def activate_form(req: func.HttpRequest) -> func.HttpResponse:
    """Activate a form after IT review."""
    from activate_form.handler import handle_activate_form

    return handle_activate_form(req)
