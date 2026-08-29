"""Lambda handler for the Triage stage."""

from __future__ import annotations

from typing import Any

from src.agents.medassist import TriageAgent
from src.lambdas._base import run_stage


def handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    return run_stage(
        event,
        required=["complaint"],
        fn=lambda d: TriageAgent().run(d["complaint"], d.get("vitals")),
    )
