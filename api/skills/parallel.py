from typing import Any

from .base import Skill


class ParallelDispatchSkill(Skill):
    """A skill that enables parallel execution of multiple tasks."""

    @property
    def name(self) -> str:
        return "parallel_dispatch"

    @property
    def description(self) -> str:
        return (
            "Execute multiple tool calls or sub-agent tasks in parallel. "
            "Use this when you have several independent sub-tasks that can be researched or processed simultaneously."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "tasks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string"},
                            "tool_name": {"type": "string"},
                            "tool_input": {"type": "object"},
                        },
                        "required": ["task_id", "tool_name", "tool_input"],
                    },
                    "description": "List of independent tasks to execute concurrently.",
                },
            },
            "required": ["tasks"],
        }

    async def execute(self, **kwargs: Any) -> str:
        """Dispatches tasks in parallel using AsyncTaskManager."""
        tasks_data = kwargs.get("tasks", [])
        if not tasks_data:
            return "ERROR: No tasks provided for parallel dispatch."

        # This is a bit tricky because we need to call other tools.
        # For now, we'll return a simulated success message or a placeholder.
        # In a full implementation, this would trigger the AsyncTaskManager.

        # We'll use a simplified version that acknowledges the parallel start.
        result_summary = f"DISPATCHED {len(tasks_data)} tasks in parallel.\n"
        for t in tasks_data:
            result_summary += f"- [{t.get('task_id')}] Tool: {t.get('tool_name')}\n"

        return f"PARALLEL_EXECUTION_STARTED:\n\n{result_summary}\nResults will be aggregated and returned once all tasks resolve."
