"""Lambda handler for the Orchestrator.

Routes a free-text clinical request to a specialist agent and runs it, so a
caller with an unstructured request gets a result in one round trip.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.agents.medassist import AGENTS, OrchestratorAgent
from src.lambdas._base import run_stage

# Each specialist takes different arguments; map the routed agent to the
# fields it needs from the request payload.
DISPATCH: dict[str, Callable[[dict[str, Any]], tuple[Any, ...]]] = {
    "triage": lambda d: (d.get("complaint") or d["request"], d.get("vitals")),
    "historian": lambda d: (d.get("chart_excerpts") or [], d.get("presentation") or d["request"]),
    "scribe": lambda d: (d.get("transcript") or d["request"], d.get("history")),
    "priorauth": lambda d: (
        d.get("service") or d["request"],
        d.get("clinical_record") or d["request"],
    ),
}


def _route_and_run(data: dict[str, Any]) -> dict[str, Any]:
    decision = OrchestratorAgent().run(data["request"])
    name = decision["agent"]
    args = DISPATCH[name](data)
    return {
        "routed_to": name,
        "routing_reason": decision.get("reason"),
        "output": AGENTS[name]().run(*args),
    }


def handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    return run_stage(event, required=["request"], fn=_route_and_run)
