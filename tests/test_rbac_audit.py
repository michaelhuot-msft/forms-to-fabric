"""Tests for the RBAC audit of Fabric workspace access."""

import sys
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "functions"))

from audit_rbac.handler import audit_workspace_access  # noqa: E402


def _assignment(
    principal_id: str,
    display_name: str,
    role: str,
    principal_type: str = "Group",
) -> dict[str, str]:
    """Helper to build a fake role-assignment dict."""
    return {
        "principal_id": principal_id,
        "principal_type": principal_type,
        "role": role,
        "display_name": display_name,
    }


_ENV = {
    "FABRIC_WORKSPACE_ID": "ws-001",
    "ALLOWED_RAW_ACCESS_GROUP": "IT-Admins",
    "FUNCTION_APP_MANAGED_IDENTITY_ID": "mi-sp-001",
}


@patch.dict("os.environ", _ENV)
@patch("audit_rbac.handler.get_workspace_users")
def test_compliant_workspace(mock_users):
    """Only the allowed admin group has a privileged role → compliant."""
    mock_users.return_value = [
        _assignment("grp-admins", "IT-Admins", "Admin", "Group"),
    ]
    report = audit_workspace_access()
    assert report.is_compliant is True
    assert report.violations == []
    assert report.total_assignments == 1


@patch.dict("os.environ", _ENV)
@patch("audit_rbac.handler.get_workspace_users")
def test_violation_non_admin_contributor(mock_users):
    """A random user with Contributor role should be flagged."""
    mock_users.return_value = [
        _assignment("grp-admins", "IT-Admins", "Admin", "Group"),
        _assignment("user-123", "Jane Doe", "Contributor", "User"),
    ]
    report = audit_workspace_access()
    assert report.is_compliant is False
    assert len(report.violations) == 1
    v = report.violations[0]
    assert v.principal_id == "user-123"
    assert v.principal_name == "Jane Doe"
    assert v.assigned_role == "Contributor"
    assert "IT-Admins" in v.reason


@patch.dict("os.environ", _ENV)
@patch("audit_rbac.handler.get_workspace_users")
def test_managed_identity_allowed(mock_users):
    """The Function App's own managed identity should not be flagged."""
    mock_users.return_value = [
        _assignment("grp-admins", "IT-Admins", "Admin", "Group"),
        _assignment("mi-sp-001", "forms-func-app", "Contributor", "ServicePrincipal"),
    ]
    report = audit_workspace_access()
    assert report.is_compliant is True
    assert report.violations == []


@patch.dict("os.environ", _ENV)
@patch("audit_rbac.handler.get_workspace_users")
def test_empty_workspace(mock_users):
    """No role assignments at all → compliant."""
    mock_users.return_value = []
    report = audit_workspace_access()
    assert report.is_compliant is True
    assert report.total_assignments == 0
    assert report.violations == []


@patch.dict("os.environ", _ENV)
@patch("audit_rbac.handler.get_workspace_users")
def test_viewer_role_allowed(mock_users):
    """Viewer role is read-only (curated layer via Power BI) and should not be flagged."""
    mock_users.return_value = [
        _assignment("grp-admins", "IT-Admins", "Admin", "Group"),
        _assignment("user-456", "John Smith", "Viewer", "User"),
    ]
    report = audit_workspace_access()
    assert report.is_compliant is True
    assert report.violations == []
    assert report.total_assignments == 2
