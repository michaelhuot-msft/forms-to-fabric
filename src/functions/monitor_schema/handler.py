"""Schema monitor — detects when clinicians modify their Microsoft Forms.

Compares the live form structure (via Microsoft Graph API) against the
local form-registry.json configuration and reports any differences.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from shared.config import get_all_form_configs
from shared.graph_client import (
    FormAccessDeniedError,
    FormNotFoundError,
    GraphClient,
)
from shared.models import FormConfig, SchemaChange, SchemaChangeReport

logger = logging.getLogger(__name__)

_graph_client: GraphClient | None = None


def _get_graph_client() -> GraphClient:
    """Return a module-level GraphClient instance (lazy-initialised)."""
    global _graph_client  # noqa: PLW0603
    if _graph_client is None:
        _graph_client = GraphClient()
    return _graph_client


def _compare_schema(
    form_config: FormConfig,
    live_questions: list[dict[str, str]],
) -> list[SchemaChange]:
    """Compare the registry fields against live questions and return changes.

    Detection rules:
      - **Added**: question ID exists in live but not in registry.
      - **Removed**: question ID exists in registry but not in live.
      - **Renamed**: question ID exists in both but the title differs from
        the registered ``field_name``.
    """
    registered = {f.question_id: f for f in form_config.fields}
    live = {q["id"]: q for q in live_questions}

    changes: list[SchemaChange] = []

    # Detect added questions
    for qid, question in live.items():
        if qid not in registered:
            changes.append(
                SchemaChange(
                    change_type="added",
                    question_id=qid,
                    new_value=question.get("title", ""),
                )
            )

    # Detect removed questions
    for qid, field in registered.items():
        if qid not in live:
            changes.append(
                SchemaChange(
                    change_type="removed",
                    question_id=qid,
                    field_name=field.field_name,
                    old_value=field.field_name,
                )
            )

    # Detect renamed questions (same ID, different title)
    for qid in registered:
        if qid in live:
            reg_name = registered[qid].field_name
            live_title = live[qid].get("title", "")
            if reg_name != live_title:
                changes.append(
                    SchemaChange(
                        change_type="renamed",
                        question_id=qid,
                        field_name=reg_name,
                        old_value=reg_name,
                        new_value=live_title,
                    )
                )

    return changes


def check_all_forms(
    client: GraphClient | None = None,
) -> list[SchemaChangeReport]:
    """Check every registered form for schema changes.

    Args:
        client: Optional ``GraphClient`` override (useful for testing).

    Returns:
        A list of ``SchemaChangeReport`` objects — one per registered form.
    """
    graph = client or _get_graph_client()
    configs = get_all_form_configs()
    reports: list[SchemaChangeReport] = []
    now = datetime.now(timezone.utc)

    for form_id, form_config in configs.items():
        try:
            live_questions = graph.get_form_questions(form_id)
        except FormNotFoundError:
            logger.warning(
                "Form '%s' (%s) not found — it may have been deleted.",
                form_config.form_name,
                form_id,
            )
            reports.append(
                SchemaChangeReport(
                    form_id=form_id,
                    form_name=form_config.form_name,
                    checked_at=now,
                    changes=[
                        SchemaChange(
                            change_type="removed",
                            question_id="*",
                            field_name=form_config.form_name,
                            old_value="entire form deleted",
                        )
                    ],
                    has_changes=True,
                )
            )
            continue
        except FormAccessDeniedError:
            logger.error(
                "Access denied for form '%s' (%s). Skipping.",
                form_config.form_name,
                form_id,
            )
            continue
        except Exception:
            logger.exception(
                "Unexpected error checking form '%s' (%s). Skipping.",
                form_config.form_name,
                form_id,
            )
            continue

        changes = _compare_schema(form_config, live_questions)
        reports.append(
            SchemaChangeReport(
                form_id=form_id,
                form_name=form_config.form_name,
                checked_at=now,
                changes=changes,
                has_changes=len(changes) > 0,
            )
        )

    return reports


def send_alert(reports: list[SchemaChangeReport]) -> None:
    """Log schema-change reports and optionally send an email alert.

    If the ``ADMIN_ALERT_EMAIL`` environment variable is set, the function
    logs a message indicating that an email *would* be sent (actual email
    delivery should be wired up to a notification service).  Otherwise it
    only writes to Application Insights / the standard logger.
    """
    for report in reports:
        change_summaries = []
        for change in report.changes:
            if change.change_type == "added":
                change_summaries.append(
                    f"  + ADDED   question '{change.question_id}': '{change.new_value}'"
                )
            elif change.change_type == "removed":
                change_summaries.append(
                    f"  - REMOVED question '{change.question_id}': '{change.old_value}'"
                )
            elif change.change_type == "renamed":
                change_summaries.append(
                    f"  ~ RENAMED question '{change.question_id}': "
                    f"'{change.old_value}' -> '{change.new_value}'"
                )

        detail = "\n".join(change_summaries)
        logger.warning(
            "Schema changes detected for form '%s' (%s) at %s:\n%s",
            report.form_name,
            report.form_id,
            report.checked_at.isoformat(),
            detail,
        )

    admin_email = os.environ.get("ADMIN_ALERT_EMAIL")
    if admin_email:
        logger.info(
            "Sending schema-change alert email to %s for %d form(s).",
            admin_email,
            len(reports),
        )
    else:
        logger.info(
            "ADMIN_ALERT_EMAIL not set — skipping email notification for "
            "%d form(s) with changes.",
            len(reports),
        )
