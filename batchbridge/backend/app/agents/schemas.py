from typing import Any, Literal

from pydantic import BaseModel, Field


class AgentAssessment(BaseModel):
    summary: str = Field(max_length=600)
    unanswered_questions: list[str] = Field(default_factory=list, max_length=5)
    confidence: Literal["low", "medium", "high"]


class TriageResult(BaseModel):
    type: Literal["triage_recommendation"] = "triage_recommendation"
    case_id: str
    possible_product_ids: list[str]
    reported_batch_number: str | None
    related_case_ids: list[str]
    missing_fields: list[str]
    follow_up_questions: list[str]
    recommendation: Literal[
        "request_information",
        "retailer_review",
        "forward_to_importer",
    ]
    confidence: Literal["low", "medium", "high"]
    rationale: list[str]
    evidence_references: list[str]
    ai_assessment: dict[str, Any] | None = None
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)


class TraceabilityResult(BaseModel):
    type: Literal["request_information", "retailer_inspections"]
    case_id: str
    matched_product_id: str | None
    matched_batch_id: str | None
    match_method: Literal["exact_sku", "exact_name", "known_alias", "unresolved"]
    confidence: Literal["low", "medium", "high"]
    product: dict[str, Any] | None
    batch: dict[str, Any] | None
    retailers: list[dict[str, Any]]
    excluded_retailers: list[dict[str, Any]]
    related_reports: list[dict[str, Any]]
    missing: list[str]
    rationale: list[str]
    evidence_references: list[str]
    ai_assessment: dict[str, Any] | None = None
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)


class EscalationResult(BaseModel):
    type: Literal["manufacturer_escalation_packet"] = "manufacturer_escalation_packet"
    case_id: str
    batch_id: str
    completed_inspections: int
    pending_inspections: int
    findings_summary: list[dict[str, Any]]
    conflicting_findings: list[dict[str, Any]]
    affected_quantity: int
    checked_quantity: int | None
    missing_evidence: list[str]
    manufacturer_questions: list[str]
    recommendation: Literal[
        "request_more_retailer_checks",
        "prepare_manufacturer_escalation",
        "continue_monitoring",
    ]
    manufacturer_id: str
    manufacturer_packet: dict[str, Any]
    rationale: list[str]
    evidence_references: list[str]
    ai_assessment: dict[str, Any] | None = None
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
