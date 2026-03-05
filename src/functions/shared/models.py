"""Pydantic models for the Forms to Fabric pipeline."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Answer(BaseModel):
    """A single answer within a form response."""

    question_id: str
    question: str
    answer: str


class FormResponse(BaseModel):
    """Incoming payload from Power Automate containing a Microsoft Forms response."""

    form_id: str
    response_id: str
    submitted_at: datetime
    respondent_email: str
    answers: list[Answer]


class FieldConfig(BaseModel):
    """Configuration for a single form field, including de-identification settings."""

    question_id: str
    field_name: str
    contains_phi: bool = False
    deid_method: Optional[str] = Field(
        default=None,
        description="De-identification method: 'hash', 'redact', 'generalize', or null",
    )
    field_type: Optional[str] = Field(
        default=None,
        description="Semantic type hint used by generalize (e.g. 'date', 'age')",
    )


class FormConfig(BaseModel):
    """Registry entry that describes how to process a specific Microsoft Form."""

    form_id: str
    form_name: str
    target_table: str
    status: str = Field(
        default="active",
        description="'active', 'pending_review', or 'inactive'",
    )
    fields: list[FieldConfig]


class ProcessingResult(BaseModel):
    """Result returned after processing a single form response."""

    status: str = Field(description="'success' or 'error'")
    response_id: str
    form_id: str
    raw_path: Optional[str] = None
    curated_path: Optional[str] = None
    message: Optional[str] = None


class SchemaChange(BaseModel):
    """A single detected change in a form's question structure."""

    change_type: str = Field(description="'added', 'removed', or 'renamed'")
    question_id: str
    field_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None


class SchemaChangeReport(BaseModel):
    """Report of all schema changes detected for a single form."""

    form_id: str
    form_name: str
    checked_at: datetime
    changes: list[SchemaChange]
    has_changes: bool = False


class RbacViolation(BaseModel):
    """A single RBAC violation found during audit."""

    principal_id: str
    principal_name: str
    principal_type: str
    assigned_role: str
    reason: str


class RbacAuditReport(BaseModel):
    """Results of an RBAC audit for a Fabric workspace."""

    workspace_id: str
    checked_at: datetime
    total_assignments: int
    violations: list[RbacViolation]
    is_compliant: bool
