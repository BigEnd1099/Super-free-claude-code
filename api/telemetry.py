"""Telemetry and Mission Management."""

import asyncio
from datetime import datetime
from typing import Any

from loguru import logger

from .websockets import manager


class ThinkingCache:
    """Tracks and caches thinking signatures for stable sessions."""

    def __init__(self):
        self.signatures: dict[str, str] = {}

    def store(self, session_id: str, signature: str):
        self.signatures[session_id] = signature

    def get(self, session_id: str) -> str | None:
        return self.signatures.get(session_id)


class MissionManager:
    def __init__(self):
        self.server_start_time = datetime.now()
        self.active_sessions: dict[str, dict[str, Any]] = {}
        self.change_log: list[dict[str, Any]] = []
        self.tool_count = 0
        self.total_tokens = 0
        self.total_cost = 0.0
        self.model_stats: dict[str, dict[str, Any]] = {}
        self.thinking_cache = ThinkingCache()
        self.stats_file = "MISSION_REPORTS/stats_v1.json"
        self._load_stats()

    def _load_stats(self):
        """Load persistent stats from disk."""
        import json
        import os
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.total_tokens = data.get("total_tokens", 0)
                    self.total_cost = data.get("total_cost", 0.0)
                    self.tool_count = data.get("tool_count", 0)
                    self.model_stats = data.get("model_stats", {})
                    # Load change log but keep it reasonable
                    self.change_log = data.get("change_log", [])[-100:]
                    logger.info(f"MISSION_CONTROL: Loaded persistent stats from {self.stats_file}")
            except Exception as e:
                logger.error(f"MISSION_CONTROL: Failed to load stats: {e}")

    def _save_stats(self):
        """Save persistent stats to disk."""
        import json
        import os
        try:
            os.makedirs(os.path.dirname(self.stats_file), exist_ok=True)
            data = {
                "total_tokens": self.total_tokens,
                "total_cost": self.total_cost,
                "tool_count": self.tool_count,
                "model_stats": self.model_stats,
                "change_log": self.change_log[-100:],
                "last_updated": datetime.now().isoformat()
            }
            with open(self.stats_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"MISSION_CONTROL: Failed to save stats: {e}")

    def start_session(self, request_id: str, model: str):
        self.active_sessions[request_id] = {
            "start_time": datetime.now(),
            "model": model,
            "tools": [],
            "events": [],
        }
        if model not in self.model_stats:
            self.model_stats[model] = {"tokens": 0, "cost": 0.0, "calls": 0}
        self.model_stats[model]["calls"] += 1

    def end_session(self, request_id: str, success: bool = True):
        if request_id in self.active_sessions:
            session = self.active_sessions[request_id]
            duration = (datetime.now() - session["start_time"]).total_seconds()
            
            # Phase 4: Forensic Analysis for failures
            analysis = None
            if not success:
                from .harness.forensics import forensic_analyzer
                analysis = forensic_analyzer.analyze(request_id, session.get("events", []))
                logger.warning(f"FORENSICS: Root cause identified: {analysis['root_cause']}")
                if analysis["recommendation"] != "none":
                    logger.info(f"FORENSICS: Recommended action: {analysis['recommendation']}")

            # --- Mission Journal Persistence ---
            try:
                import json
                import os
                report_dir = "MISSION_REPORTS"
                os.makedirs(report_dir, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                report_file = os.path.join(report_dir, f"mission_{timestamp}_{request_id[:8]}.md")
                
                with open(report_file, "w", encoding="utf-8") as f:
                    f.write(f"# Mission Report: {request_id}\n\n")
                    f.write(f"- **Timestamp:** {datetime.now().isoformat()}\n")
                    f.write(f"- **Model:** {session.get('model')}\n")
                    f.write(f"- **Status:** {'SUCCESS' if success else 'FAILED'}\n")
                    f.write(f"- **Duration:** {duration:.2f}s\n")
                    f.write(f"- **Tokens:** {session.get('total_tokens', 0)}\n\n")
                    
                    f.write("## Tool Activity\n")
                    for tool in session.get("tools", []):
                        f.write(f"- {tool}\n")
                    f.write("\n")
                    
                    if analysis:
                        f.write("## Forensic Analysis\n")
                        f.write(f"**Root Cause:** {analysis['root_cause']}\n\n")
                        f.write(f"**Recommendation:** {analysis['recommendation']}\n\n")
                        
                    f.write("## Event Stream\n")
                    for event in session.get("events", []):
                        f.write(f"### {event['type']} ({event['time']})\n")
                        f.write("```json\n")
                        f.write(json.dumps(event, indent=2) + "\n")
                        f.write("```\n\n")
                
                logger.info(f"MISSION_JOURNAL: Report saved to {report_file}")
            except Exception as e:
                logger.error(f"MISSION_JOURNAL: Failed to save report: {e}")

            logger.info(
                "SESSION_ENDED: id={} duration={:.2f}s tokens={} status={}",
                request_id,
                duration,
                session.get("total_tokens", 0),
                "SUCCESS" if success else "FAILED"
            )
            del self.active_sessions[request_id]
            self._save_stats()

    def log_event(self, request_id: str, event_type: str, data: dict):
        """Track events for forensic analysis."""
        if request_id in self.active_sessions:
            self.active_sessions[request_id]["events"].append({
                "type": event_type,
                "time": datetime.now().isoformat(),
                **data
            })

    def log_tokens(
        self, tokens: int, model: str | None = None, request_id: str | None = None
    ):
        self.total_tokens += tokens

        # Determine cost based on model (simplified mapping)
        cost_rate = 15.0  # Default $15 per 1M
        if model:
            model_lower = model.lower()
            if "opus" in model_lower:
                cost_rate = 75.0
            elif "sonnet" in model_lower:
                cost_rate = 15.0
            elif "haiku" in model_lower:
                cost_rate = 1.25
            elif "llama-3.3-70b" in model_lower:
                cost_rate = 0.9
            elif "flash" in model_lower:
                cost_rate = 0.1

        cost = (tokens / 1000000.0) * cost_rate
        self.total_cost += cost

        if model and model in self.model_stats:
            self.model_stats[model]["tokens"] += tokens
            self.model_stats[model]["cost"] += cost

        if request_id and request_id in self.active_sessions:
            self.active_sessions[request_id]["total_tokens"] = (
                self.active_sessions[request_id].get("total_tokens", 0) + tokens
            )
        self._save_stats()

    def log_tool(self, request_id: str, tool_name: str, input_data: dict):
        self.tool_count += 1
        if request_id in self.active_sessions:
            self.active_sessions[request_id]["tools"].append(tool_name)

        # Broadcast via WebSocket
        asyncio.create_task(
            manager.broadcast(
                {
                    "type": "tool_use",
                    "tool": tool_name,
                    "input": input_data,
                    "request_id": request_id,
                    "time": datetime.now().isoformat(),
                }
            )
        )

        # Track file changes
        if tool_name in [
            "Edit",
            "WriteFile",
            "ReplaceFileContent",
            "multi_replace_file_content",
        ]:
            file_path = (
                input_data.get("filePath")
                or input_data.get("path")
                or input_data.get("TargetFile")
            )
            if file_path:
                self.change_log.append(
                    {
                        "time": datetime.now().isoformat(),
                        "file": file_path,
                        "type": "edit"
                        if "replace" in tool_name.lower() or tool_name == "Edit"
                        else "create",
                        "request_id": request_id,
                    }
                )
        self._save_stats()
    def verify_thinking(self, request_id: str, content: str) -> bool:
        """Verify that a thinking signature or block is present in the response."""
        has_thinking = False
        if "<thinking>" in content.lower() or "thought:" in content.lower():
            has_thinking = True
        
        if request_id in self.active_sessions:
            self.active_sessions[request_id]["has_thinking"] = has_thinking
            if not has_thinking:
                self.log_event(request_id, "thinking_missing", {"content_snippet": content[:200]})
        
        return has_thinking

    def get_status(self):
        # MISSION CONTROL: Use dict copy to prevent concurrency errors during iteration
        sessions_snapshot = {}
        for rid, s in self.active_sessions.items():
            duration = (datetime.now() - s["start_time"]).total_seconds()
            sessions_snapshot[rid] = {
                "model": s["model"],
                "duration": f"{duration:.1f}s",
                "tools": s["tools"],
                "tokens": s.get("total_tokens", 0),
            }

        uptime_seconds = int((datetime.now() - self.server_start_time).total_seconds())
        return {
            "status": "healthy",
            "uptime": f"{uptime_seconds}s",
            "start_time": self.server_start_time.isoformat(),
            "active_count": len(sessions_snapshot),
            "tool_count": self.tool_count,
            "total_tokens": self.total_tokens,
            "total_cost": round(self.total_cost, 4),
            "recent_changes": self.change_log[-15:],
            "active_sessions": sessions_snapshot,
            "model_stats": self.model_stats,
        }


mission_manager = MissionManager()
