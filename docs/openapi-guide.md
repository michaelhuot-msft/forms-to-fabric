# Using OpenAPI with Forms to Fabric

The Forms to Fabric API exposes an **OpenAPI 3.0.3 specification** at a built-in endpoint. You can use this spec to explore the API interactively, generate client SDKs, and integrate with API management tools.

## The `/api/openapi` Endpoint

| | |
|---|---|
| **URL** | `GET https://<your-function-app>.azurewebsites.net/api/openapi` |
| **Auth** | Anonymous (no function key required) |
| **Response** | `application/json` — OpenAPI 3.0.3 document |

This endpoint is served without authentication so that tools like Swagger UI and API Management can fetch it without embedding a function key.

All **other** endpoints (`/api/process-response`, `/api/register-form`, `/api/activate-form`, `/api/generate-flow`) still require a function key passed in the `x-functions-key` header or the `code` query parameter.

---

## What the Spec Covers

| Endpoint | Method | Tag | Description |
|---|---|---|---|
| `/api/process-response` | POST | Pipeline | Ingest a form submission into Fabric OneLake |
| `/api/register-form` | POST | Registry | Self-service form registration |
| `/api/activate-form` | POST | Registry | IT approval to activate a pending form |
| `/api/generate-flow` | GET | Integration | Download a Power Automate flow definition |

The spec includes:

- **Request and response schemas** for all endpoints, derived from the Pydantic models in `shared/models.py`
- **Example payloads** for structured and raw-passthrough submissions
- **Status codes** with descriptions for every response variant
- **Security scheme** definitions for both header (`x-functions-key`) and query (`code`) key formats

---

## Interactive Exploration with Swagger UI

Paste the spec URL into any OpenAPI viewer.

### Option A — swagger.io online editor

1. Open [https://editor.swagger.io](https://editor.swagger.io)
2. Choose **File → Import URL**
3. Enter `https://<your-function-app>.azurewebsites.net/api/openapi`

### Option B — Docker (local)

```bash
docker run -p 8080:8080 \
  -e SWAGGER_JSON_URL="https://<your-function-app>.azurewebsites.net/api/openapi" \
  swaggerapi/swagger-ui
```

Open [http://localhost:8080](http://localhost:8080) in your browser.

---

## Azure API Management Integration

The spec makes it straightforward to import the API into [Azure API Management (APIM)](https://learn.microsoft.com/azure/api-management/).

1. In the Azure Portal, open your APIM instance.
2. Go to **APIs → Add API → OpenAPI**.
3. Enter the spec URL: `https://<your-function-app>.azurewebsites.net/api/openapi`
4. Set the **API URL suffix** (e.g. `forms-to-fabric`) and click **Create**.

APIM will provision all four operations automatically. You can then add policies (rate limiting, IP filtering, caching) without touching the Function App code.

> **Tip:** Use APIM's **Subscription Keys** to front the Function App key so end-users never see the raw Azure Functions key.

---

## Generating a Client SDK

The spec can be used with any OpenAPI code generator.

### Python client with `openapi-python-client`

```bash
pip install openapi-python-client
openapi-python-client generate \
  --url "https://<your-function-app>.azurewebsites.net/api/openapi"
```

### TypeScript / JavaScript with `openapi-typescript`

```bash
npx openapi-typescript \
  "https://<your-function-app>.azurewebsites.net/api/openapi" \
  --output forms-to-fabric-types.ts
```

### Using `openapi-generator-cli` (any language)

```bash
docker run --rm \
  -v "${PWD}:/local" openapitools/openapi-generator-cli generate \
  -i "https://<your-function-app>.azurewebsites.net/api/openapi" \
  -g python \
  -o /local/forms-to-fabric-client
```

Replace `-g python` with any [supported generator](https://openapi-generator.tech/docs/generators) (e.g. `csharp`, `java`, `go`, `typescript-fetch`).

---

## Validating the Spec Locally

To validate that the spec is well-formed during development:

```bash
pip install openapi-spec-validator
python - <<'EOF'
import json, sys
from openapi_spec_validator import validate

# Ensure the functions path is importable
sys.path.insert(0, "src/functions")
from openapi_spec.handler import build_openapi_spec

validate(build_openapi_spec())
print("Spec is valid ✓")
EOF
```

---

## Keeping the Spec Up to Date

The spec is generated dynamically by `src/functions/openapi_spec/handler.py`. When you add or modify an HTTP endpoint:

1. Update `build_openapi_spec()` in `handler.py` to reflect the new path, parameters, or response schemas.
2. Update the corresponding tests in `tests/test_openapi_spec.py`.
3. Run `python -m pytest tests/test_openapi_spec.py -v` to verify the spec structure.

---

## Related Documentation

- [Architecture overview](architecture.md) — end-to-end data flow diagram
- [Admin guide](admin-guide.md) — form registry management and activation workflow
- [Setup guide](setup-guide.md) — deployment instructions
