"""Lambda handler for the Historian stage."""

from __future__ import annotations

from src.agents.medassist import HistorianAgent
from src.lambdas._base import run_stage


def handler(event: dict, context: object) -> dict:
    return run_stage(
        event,
        required=["presentation"],
        fn=lambda d: HistorianAgent().run(
            d.get("chart_excerpts") or [], d["presentation"]
        ),
    )
