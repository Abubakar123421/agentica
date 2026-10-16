"""Bounded BatchBridge agents."""

from app.agents.escalation import run_escalation_agent
from app.agents.traceability import run_traceability_agent
from app.agents.triage import run_triage_agent

AGENT_RUNNERS = {
    "triage": run_triage_agent,
    "traceability": run_traceability_agent,
    "escalation": run_escalation_agent,
}

__all__ = ["AGENT_RUNNERS"]
