import json
from typing import Any

from langchain_groq import ChatGroq

from app.agents.schemas import AgentAssessment
from app.config import get_settings


async def assess_with_groq(agent_type: str, evidence: dict[str, Any]) -> dict | None:
    settings = get_settings()
    if not settings.groq_api_key:
        return None
    prompt = (
        f"You are the bounded {agent_type} agent in a food batch investigation. "
        "Summarize only the supplied evidence and list useful unanswered questions. "
        "A complaint or visual finding is not laboratory proof. Never declare a batch safe or "
        "contaminated. Never invent identifiers, retailers, quantities, findings, or test results. "
        "Return the requested structured assessment.\n\n"
        f"Evidence:\n{json.dumps(evidence, default=str)}"
    )
    try:
        model = ChatGroq(
            model=settings.groq_model,
            temperature=0,
            api_key=settings.groq_api_key,
            timeout=30,
            max_retries=1,
        ).with_structured_output(AgentAssessment)
        result = await model.ainvoke(prompt)
        return result.model_dump() if hasattr(result, "model_dump") else dict(result)
    except Exception as exc:
        return {"unavailable": True, "reason": type(exc).__name__}
