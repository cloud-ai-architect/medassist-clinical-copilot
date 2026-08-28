"""MedAssist clinical agents.

Four specialists behind an orchestrator:

    Triage      urgency and red-flag detection      (fast tier)
    Historian   summarises prior chart history      (standard tier)
    Scribe      drafts a SOAP visit note            (standard tier)
    PriorAuth   drafts a prior-authorisation packet (standard tier)

Model tier is chosen per task. Triage is a short structured classification
and runs on the cheapest model; the drafting agents need more capable
generation. See src.common for the tier definitions.

Every agent is advisory. Nothing here is a clinical decision: output is
drafted for a clinician to review, edit and sign, and each agent is
instructed to surface uncertainty rather than resolve it silently.
"""

from __future__ import annotations

from typing import Any

from src.common import MODEL_FAST, MODEL_STANDARD, BaseAgent

DISCLAIMER = (
    "This output is a draft for clinician review. It is not a diagnosis and "
    "not a treatment recommendation."
)


class TriageAgent(BaseAgent):
    """Assess urgency and surface red flags from a presenting complaint."""

    NAME = "triage"
    MODEL = MODEL_FAST
    SYSTEM_PROMPT = (
        "You are a clinical triage assistant supporting a licensed clinician.\n"
        "Given a presenting complaint, assess urgency and surface red flags.\n"
        "You do not diagnose and you do not recommend treatment.\n"
        "If the information is insufficient to judge urgency, say so explicitly "
        "rather than guessing.\n"
        "Respond with JSON only, matching this shape:\n"
        '{"acuity": "emergent|urgent|routine|insufficient_information",\n'
        ' "red_flags": ["..."],\n'
        ' "rationale": "one or two sentences",\n'
        ' "recommended_next_step": "what the clinician should consider next",\n'
        ' "missing_information": ["..."]}'
    )

    def handle(self, complaint: str, vitals: dict[str, Any] | None = None) -> dict[str, Any]:
        prompt = f"Presenting complaint:\n{complaint}\n"
        if vitals:
            rendered = "\n".join(f"  {k}: {v}" for k, v in vitals.items())
            prompt += f"\nVitals:\n{rendered}\n"
        result = self.invoke_json(prompt)
        result["disclaimer"] = DISCLAIMER
        return result


class HistorianAgent(BaseAgent):
    """Summarise relevant prior history for the current presentation."""

    NAME = "historian"
    MODEL = MODEL_STANDARD
    SYSTEM_PROMPT = (
        "You summarise a patient's prior chart for a clinician who is seeing "
        "them now. Include only history relevant to the current presentation.\n"
        "Every statement must be traceable to the supplied records. If "
        "something is not in the records, do not state it -- list it under "
        "gaps instead.\n"
        "Respond with JSON only:\n"
        '{"relevant_history": ["..."],\n'
        ' "active_medications": ["..."],\n'
        ' "allergies": ["..."],\n'
        ' "prior_episodes": ["..."],\n'
        ' "gaps": ["information a clinician would want that is absent"]}'
    )

    def handle(self, chart_excerpts: list[str], presentation: str) -> dict[str, Any]:
        records = "\n\n---\n\n".join(chart_excerpts) if chart_excerpts else "(no records supplied)"
        prompt = (
            f"Current presentation:\n{presentation}\n\n"
            f"Prior chart records:\n{records}"
        )
        result = self.invoke_json(prompt)
        result["disclaimer"] = DISCLAIMER
        return result


class ScribeAgent(BaseAgent):
    """Draft a SOAP-structured visit note."""

    NAME = "scribe"
    MODEL = MODEL_STANDARD
    SYSTEM_PROMPT = (
        "You draft clinical visit notes in SOAP format for clinician review.\n"
        "Use only what the encounter transcript supports. Do not invent "
        "findings, values, or history. Where the transcript is ambiguous, "
        "write [clarify: ...] inline so the clinician can resolve it.\n"
        "Respond with JSON only:\n"
        '{"subjective": "...", "objective": "...",\n'
        ' "assessment": "...", "plan": "...",\n'
        ' "clarifications_needed": ["..."]}'
    )

    def handle(self, transcript: str, history: dict[str, Any] | None = None) -> dict[str, Any]:
        prompt = f"Encounter transcript:\n{transcript}\n"
        if history:
            relevant = history.get("relevant_history") or []
            if relevant:
                prompt += "\nRelevant prior history:\n" + "\n".join(f"  - {h}" for h in relevant)
        result = self.invoke_json(prompt, max_tokens=3000)
        result["disclaimer"] = DISCLAIMER
        return result


class PriorAuthAgent(BaseAgent):
    """Draft a prior-authorisation justification."""

    NAME = "priorauth"
    MODEL = MODEL_STANDARD
    SYSTEM_PROMPT = (
        "You draft prior-authorisation requests for a clinician to review and "
        "submit. Payers reject requests that assert unsupported medical "
        "necessity, so every justification point must cite something in the "
        "supplied clinical record.\n"
        "List anything the payer will likely require that is missing.\n"
        "Respond with JSON only:\n"
        '{"requested_service": "...",\n'
        ' "medical_necessity": ["each point, grounded in the record"],\n'
        ' "supporting_evidence": ["what in the record supports each point"],\n'
        ' "missing_documentation": ["..."],\n'
        ' "draft_letter": "the full letter text"}'
    )

    def handle(self, service: str, clinical_record: str) -> dict[str, Any]:
        prompt = (
            f"Requested service:\n{service}\n\n"
            f"Clinical record:\n{clinical_record}"
        )
        result = self.invoke_json(prompt, max_tokens=3000)
        result["disclaimer"] = DISCLAIMER
        return result


class OrchestratorAgent(BaseAgent):
    """Route an inbound clinical request to the right specialist."""

    NAME = "orchestrator"
    MODEL = MODEL_FAST
    SYSTEM_PROMPT = (
        "You route clinical requests to one specialist agent.\n"
        "Options:\n"
        "  triage     - urgency assessment of a presenting complaint\n"
        "  historian  - summarising prior chart history\n"
        "  scribe     - drafting a visit note from an encounter\n"
        "  priorauth  - drafting a prior-authorisation request\n"
        "Respond with JSON only:\n"
        '{"agent": "triage|historian|scribe|priorauth",\n'
        ' "reason": "one sentence"}'
    )

    VALID = {"triage", "historian", "scribe", "priorauth"}

    def handle(self, request: str) -> dict[str, Any]:
        result = self.invoke_json(f"Request:\n{request}")
        agent = result.get("agent")
        if agent not in self.VALID:
            # Triage is the safe default: it is the agent that escalates.
            result = {
                "agent": "triage",
                "reason": f"router returned unknown agent {agent!r}; defaulting to triage",
            }
        return result


AGENTS: dict[str, type[BaseAgent]] = {
    "triage": TriageAgent,
    "historian": HistorianAgent,
    "scribe": ScribeAgent,
    "priorauth": PriorAuthAgent,
    "orchestrator": OrchestratorAgent,
}

__all__ = [
    "AGENTS",
    "HistorianAgent",
    "OrchestratorAgent",
    "PriorAuthAgent",
    "ScribeAgent",
    "TriageAgent",
]
