"""Microsoft Graph API client for retrieving Microsoft Forms data."""

from __future__ import annotations

import logging
import os
from typing import Any

import requests
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)

_DEFAULT_GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
_REQUEST_TIMEOUT_SECONDS = 30


class GraphAPIError(Exception):
    """Raised when the Graph API returns an unexpected error."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(f"Graph API error {status_code}: {message}")


class FormNotFoundError(GraphAPIError):
    """Raised when the requested form does not exist (HTTP 404)."""

    def __init__(self, form_id: str) -> None:
        self.form_id = form_id
        super().__init__(404, f"Form '{form_id}' not found")


class FormAccessDeniedError(GraphAPIError):
    """Raised when access to the form is denied (HTTP 403)."""

    def __init__(self, form_id: str) -> None:
        self.form_id = form_id
        super().__init__(403, f"Access denied to form '{form_id}'")


class GraphClient:
    """Client for Microsoft Graph API operations on Microsoft Forms.

    Uses ``DefaultAzureCredential`` for authentication and supports a
    configurable base URL via the ``GRAPH_API_BASE_URL`` environment variable.
    """

    def __init__(self, credential: DefaultAzureCredential | None = None) -> None:
        self._credential = credential or DefaultAzureCredential()
        self._base_url = os.environ.get(
            "GRAPH_API_BASE_URL", _DEFAULT_GRAPH_BASE_URL
        ).rstrip("/")

    def _get_access_token(self) -> str:
        """Acquire a bearer token for Microsoft Graph."""
        token = self._credential.get_token("https://graph.microsoft.com/.default")
        return token.token

    def _request(self, method: str, path: str) -> Any:
        """Send an authenticated request to the Graph API.

        Args:
            method: HTTP method (GET, POST, etc.).
            path: API path relative to the base URL (e.g. ``/forms/{id}/questions``).

        Returns:
            Parsed JSON response body.

        Raises:
            FormNotFoundError: If the resource returns 404.
            FormAccessDeniedError: If the resource returns 403.
            GraphAPIError: For other non-success status codes.
            requests.exceptions.Timeout: If the request times out.
        """
        url = f"{self._base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self._get_access_token()}",
            "Accept": "application/json",
        }

        try:
            response = requests.request(
                method, url, headers=headers, timeout=_REQUEST_TIMEOUT_SECONDS
            )
        except requests.exceptions.Timeout:
            logger.error("Graph API request timed out: %s %s", method, url)
            raise

        if response.status_code == 404:
            raise FormNotFoundError(path)
        if response.status_code == 403:
            raise FormAccessDeniedError(path)
        if not response.ok:
            raise GraphAPIError(response.status_code, response.text)

        return response.json()

    def get_form_questions(self, form_id: str) -> list[dict[str, str]]:
        """Retrieve the list of questions for a Microsoft Form.

        Args:
            form_id: The unique identifier of the form.

        Returns:
            A list of dicts, each containing ``id``, ``title``, and ``type``
            keys describing a question in the form.

        Raises:
            FormNotFoundError: If the form does not exist.
            FormAccessDeniedError: If access to the form is denied.
            GraphAPIError: For other Graph API errors.
        """
        data = self._request("GET", f"/forms/{form_id}/questions")
        questions: list[dict[str, str]] = []
        for item in data.get("value", []):
            questions.append(
                {
                    "id": item["id"],
                    "title": item.get("title", ""),
                    "type": item.get("type", ""),
                }
            )
        return questions

    def get_form_metadata(self, form_id: str) -> dict[str, str]:
        """Retrieve metadata (title, description) for a Microsoft Form.

        Args:
            form_id: The unique identifier of the form.

        Returns:
            A dict with ``title`` and ``description`` keys.

        Raises:
            FormNotFoundError: If the form does not exist.
            FormAccessDeniedError: If access to the form is denied.
            GraphAPIError: For other Graph API errors.
        """
        data = self._request("GET", f"/forms/{form_id}")
        return {
            "title": data.get("title", ""),
            "description": data.get("description", ""),
        }
