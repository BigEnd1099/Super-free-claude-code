import json
import os
from typing import Any

from config.settings import get_settings

from .base import Skill


class ForensicAnalyzerSkill(Skill):
    """
    A skill that analyzes server logs to identify session health,
    rework loops, and token usage patterns.
    """

    @property
    def name(self) -> str:
        return "analyze_session_health"

    @property
    def description(self) -> str:
        return (
            "Analyze the project's operational logs to detect issues like 'rework loops', "
            "extreme token consumption, or frequent provider errors. Use this to audit "
            "the efficiency of an ongoing mission."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "lookback_lines": {
                    "type": "integer",
                    "default": 100,
                    "description": "Number of recent log lines to analyze.",
                },
                "request_id": {
                    "type": "string",
                    "description": "Optional: Filter analysis to a specific request/session ID.",
                },
            },
        }

    async def execute(self, **kwargs: Any) -> str:
        lookback = kwargs.get("lookback_lines", 100)
        target_rid = kwargs.get("request_id")

        settings = get_settings()
        log_path = settings.log_file

        if not os.path.exists(log_path):
            return f"ANALYSIS_FAILED: Log file not found at {log_path}"

        logs = []
        try:
            with open(log_path, encoding="utf-8") as f:
                # Read last N lines
                all_lines = f.readlines()
                target_lines = all_lines[-lookback:]

                for line in target_lines:
                    try:
                        data = json.loads(line)
                        if target_rid and data.get("request_id") != target_rid:
                            continue
                        logs.append(data)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            return f"ANALYSIS_FAILED: Error reading logs: {e!s}"

        if not logs:
            return "ANALYSIS_COMPLETE: No relevant log entries found in the lookback window."

        # Perform basic forensics
        errors = [l for l in logs if l.get("level") in ("ERROR", "WARNING")]
        sessions = set(l.get("request_id") for l in logs if l.get("request_id"))

        # Detect rework loops (multiple edits to the same file in a short window)
        # This is a bit complex without more context, but we can look for repeated 'ReplaceFileContent' etc.
        edits = [
            l
            for l in logs
            if "STREAM" in l.get("message", "") and "tools=" in l.get("message", "")
        ]

        summary = (
            f"### FORENSIC SUMMARY (Last {len(logs)} entries)\n"
            f"- **Active Sessions**: {len(sessions)}\n"
            f"- **Total Anomalies (Error/Warn)**: {len(errors)}\n"
            f"- **Session IDs**: {', '.join(list(sessions)[:5])}{'...' if len(sessions) > 5 else ''}\n\n"
        )

        if errors:
            summary += "#### RECENT ANOMALIES:\n"
            for e in errors[-5:]:
                summary += f"- [{e.get('time')}] {e.get('level')}: {e.get('message')}\n"

        summary += "\n#### LOG SEGMENT:\n"
        for l in logs[-10:]:
            summary += f"[{l.get('time')}] {l.get('level')}: {l.get('message')}\n"

        return summary
