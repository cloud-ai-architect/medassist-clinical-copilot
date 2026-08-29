"""Lambda handler for the Scribe stage."""

from __future__ import annotations

from typing import Any

from src.agents.medassist import ScribeAgent
from src.lambdas._base import run_stage


def handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    return run_stage(
        event,
        required=["transcript"],
        fn=lambda d: ScribeAgent().run(d["transcript"], d.get("history")),
    )
