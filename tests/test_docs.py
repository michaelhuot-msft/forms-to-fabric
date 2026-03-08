"""Regression tests for documentation that describes the current workflow."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_readme_matches_current_repo_structure() -> None:
    readme = _read("README.md")

    assert "power-bi/" not in readme
    assert "Redeploy.ps1" in readme
    assert "install-hooks.sh" in readme


def test_registration_docs_match_current_flow_creation_workflow() -> None:
    template = _read("docs/registration-form-template.md")

    assert "including auto-creating the data pipeline flow" not in template
    assert "Azure Function calls Flow API" not in template
    assert "returns the `flow_create_body` payload" in template
    assert "Power Automate posts payload to Flow API" in template


def test_user_docs_do_not_ship_registration_link_placeholder() -> None:
    for relative_path in ("docs/clinician-guide.md", "docs/faq.md"):
        assert "[registration form link placeholder]" not in _read(relative_path)


def test_future_workspace_doc_is_clearly_marked_not_current() -> None:
    workspace_doc = _read("docs/workspace-architecture.md")

    assert "Future-state reference only" in workspace_doc
    assert "single Fabric workspace and Lakehouse" in workspace_doc


def test_updated_mermaid_blocks_do_not_use_html_breaks() -> None:
    for relative_path in (
        "docs/clinician-guide.md",
        "docs/registration-form-template.md",
    ):
        content = _read(relative_path)
        mermaid_blocks = re.findall(r"```mermaid\n(.*?)```", content, flags=re.DOTALL)

        assert mermaid_blocks
        for block in mermaid_blocks:
            assert "<br" not in block.lower()
