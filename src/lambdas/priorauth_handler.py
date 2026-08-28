"""Lambda handler for the Prior Authorisation stage."""

from __future__ import annotations

from src.agents.medassist import PriorAuthAgent
from src.lambdas._base import run_stage


def handler(event: dict, context: object) -> dict:
    return run_stage(
        event,
        required=["service", "clinical_record"],
        fn=lambda d: PriorAuthAgent().run(d["service"], d["clinical_record"]),
    )
