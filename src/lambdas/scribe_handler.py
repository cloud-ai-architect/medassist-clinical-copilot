"""Lambda handler for the Scribe stage."""

from __future__ import annotations

from src.agents.medassist import ScribeAgent
from src.lambdas._base import run_stage


def handler(event: dict, context: object) -> dict:
    return run_stage(
        event,
        required=["transcript"],
        fn=lambda d: ScribeAgent().run(d["transcript"], d.get("history")),
    )
