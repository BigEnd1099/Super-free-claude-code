from typing import Any

from .base import Skill


class BrainstormSkill(Skill):
    """A skill that forces structural planning."""

    @property
    def name(self) -> str:
        return "brainstorm_plan"

    @property
    def description(self) -> str:
        return (
            "Create a structured, multi-step execution plan for a complex task. "
            "Use this BEFORE writing any code or executing sub-tasks to ensure architectural integrity."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "objective": {
                    "type": "string",
                    "description": "The high-level goal to achieve.",
                },
                "constraints": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Any technical or project constraints.",
                },
                "steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "step_id": {"type": "integer"},
                            "action": {"type": "string"},
                            "agent_type": {
                                "type": "string",
                                "description": "Which specialist should handle this step.",
                            },
                        },
                    },
                },
            },
            "required": ["objective", "steps"],
        }

    async def execute(self, **kwargs: Any) -> str:
        """Returns a formatted confirmation of the plan."""
        objective = kwargs.get("objective")
        steps = kwargs.get("steps", [])

        plan_str = f"Plan for: {objective}\n"
        for s in steps:
            plan_str += f"- Step {s.get('step_id')}: {s.get('action')} (Assigned: {s.get('agent_type')})\n"

        return f"PLAN_LOCKED: The following architectural strategy has been registered:\n\n{plan_str}"
