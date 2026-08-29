"""Lambda handler for the Prior Authorisation stage."""

from __future__ import annotations

from typing import Any

from src.agents.medassist import PriorAuthAgent
from src.lambdas._base import run_stage


def handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    return run_stage(
        event,
        required=["service", "clinical_record"],
        fn=lambda d: PriorAuthAgent().run(d["service"], d["clinical_record"]),
    )
