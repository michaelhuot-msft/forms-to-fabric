"""RBAC audit logic for Fabric workspace access control.

Ensures that the raw lakehouse layer (containing PHI) is only
accessible by the designated IT admin group and the Function App
managed identity.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from shared.fabric_client import get_workspace_users
from shared.models import RbacAuditReport, RbacViolation

logger = logging.getLogger(__name__)

# Roles that grant write/manage access to raw-layer data
_PRIVILEGED_ROLES = {"Admin", "Member", "Contributor"}


def audit_workspace_access(workspace_id: str | None = None) -> RbacAuditReport:
    """Audit Fabric workspace role assignments for PHI-layer compliance.

    Retrieves all role assignments and flags any principal that holds a
    privileged role (Admin / Member / Contributor) unless it belongs to the
    allowed admin group or is the Function App's own managed identity.

    Args:
        workspace_id: Optional workspace GUID override.  Falls back to the
            ``FABRIC_WORKSPACE_ID`` environment variable.

    Returns:
        An :class:`RbacAuditReport` summarising the findings.
    """
    wid = workspace_id or os.environ.get("FABRIC_WORKSPACE_ID", "")
    allowed_group = os.environ.get("ALLOWED_RAW_ACCESS_GROUP", "IT-Admins")
    managed_identity_id = os.environ.get("FUNCTION_APP_MANAGED_IDENTITY_ID", "")

    assignments = get_workspace_users(wid)
    violations: list[RbacViolation] = []

    for assignment in assignments:
        role = assignment.get("role", "")
        principal_id = assignment.get("principal_id", "")
        principal_name = assignment.get("display_name", "")
        principal_type = assignment.get("principal_type", "")

        if role not in _PRIVILEGED_ROLES:
            continue

        # Allow the Function App managed identity
        if managed_identity_id and principal_id == managed_identity_id:
            continue

        # Allow the designated admin group
        if principal_name == allowed_group:
            continue

        violations.append(
            RbacViolation(
                principal_id=principal_id,
                principal_name=principal_name,
                principal_type=principal_type,
                assigned_role=role,
                reason=(
                    f"Principal '{principal_name}' has '{role}' role but is not in "
                    f"the allowed group '{allowed_group}'"
                ),
            )
        )

    report = RbacAuditReport(
        workspace_id=wid,
        checked_at=datetime.now(timezone.utc),
        total_assignments=len(assignments),
        violations=violations,
        is_compliant=len(violations) == 0,
    )

    logger.info(
        "RBAC audit complete for workspace %s: %d assignments, %d violations, compliant=%s",
        wid,
        report.total_assignments,
        len(violations),
        report.is_compliant,
    )

    return report


def send_audit_alert(report: RbacAuditReport) -> None:
    """Log audit results to Application Insights.

    Compliant reports are logged at INFO level.  Non-compliant reports
    are logged at WARNING with full violation details so that
    Application Insights alerts can trigger on them.
    """
    if report.is_compliant:
        logger.info(
            "RBAC audit PASSED for workspace %s — %d assignments, 0 violations.",
            report.workspace_id,
            report.total_assignments,
        )
    else:
        for v in report.violations:
            logger.warning(
                "RBAC VIOLATION in workspace %s: %s (%s) has role '%s'. %s",
                report.workspace_id,
                v.principal_name,
                v.principal_type,
                v.assigned_role,
                v.reason,
            )
        logger.warning(
            "RBAC audit FAILED for workspace %s — %d violation(s) out of %d assignments.",
            report.workspace_id,
            len(report.violations),
            report.total_assignments,
        )
