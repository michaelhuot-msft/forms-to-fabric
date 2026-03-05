"""Azure Function App entry point (v2 programming model).

Registers the HTTP-triggered function that receives Microsoft Forms
responses from Power Automate and writes them to Microsoft Fabric OneLake.
"""

import azure.functions as func

from process_response.handler import handle_form_response

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


@app.route(route="process-response", methods=["POST"])
def process_response(req: func.HttpRequest) -> func.HttpResponse:
    """HTTP trigger that accepts a form response payload from Power Automate."""
    return handle_form_response(req)
