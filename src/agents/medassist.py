"""Main agent for MedAssist."""

from src.common import BaseAgent, MedassistTask


SYSTEM_PROMPT = """You are MedAssist, an expert agent.

Your job: handle the task at hand using the tools available to you.
Be specific, accurate, and concise.
"""


class MedassistAgent(BaseAgent):
    NAME = "langgraph"

    def handle(self, task: MedassistTask, message: str = "") -> str:
        return self.invoke_claude(
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": message or "Begin."}],
        )
