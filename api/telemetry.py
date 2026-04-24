"""Telemetry and Mission Management."""

import asyncio
import json
from datetime import datetime
from typing import Any

from loguru import logger

from .websockets import manager


class MissionManager:
    def __init__(self):
        self.active_sessions: dict[str, dict[str, Any]] = {}
        self.change_log: list[dict[str, Any]] = []
        self.tool_count = 0
        self.total_tokens = 0
        self.total_cost = 0.0
        self.model_stats: dict[str, dict[str, Any]] = {}

    def start_session(self, request_id: str, model: str):
        self.active_sessions[request_id] = {
            "start_time": datetime.now(),
            "model": model,
            "tools": [],
        }
        if model not in self.model_stats:
            self.model_stats[model] = {"tokens": 0, "cost": 0.0, "calls": 0}
        self.model_stats[model]["calls"] += 1

    def end_session(self, request_id: str):
        if request_id in self.active_sessions:
            session = self.active_sessions[request_id]
            duration = (datetime.now() - session["start_time"]).total_seconds()
            logger.info("SESSION_ENDED: id={} duration={:.2f}s tokens={}", 
                        request_id, duration, session.get("total_tokens", 0))
            del self.active_sessions[request_id]

    def log_tokens(self, tokens: int, model: str | None = None, request_id: str | None = None):
        self.total_tokens += tokens
        
        # Determine cost based on model (simplified mapping)
        cost_rate = 15.0  # Default $15 per 1M
        if model:
            model_lower = model.lower()
            if "opus" in model_lower: cost_rate = 75.0
            elif "sonnet" in model_lower: cost_rate = 15.0
            elif "haiku" in model_lower: cost_rate = 1.25
            elif "llama-3.3-70b" in model_lower: cost_rate = 0.9
            elif "flash" in model_lower: cost_rate = 0.1
            
        cost = (tokens / 1000000.0) * cost_rate
        self.total_cost += cost
        
        if model and model in self.model_stats:
            self.model_stats[model]["tokens"] += tokens
            self.model_stats[model]["cost"] += cost
            
        if request_id and request_id in self.active_sessions:
            self.active_sessions[request_id]["total_tokens"] = self.active_sessions[request_id].get("total_tokens", 0) + tokens

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
        if tool_name in ["Edit", "WriteFile", "ReplaceFileContent", "multi_replace_file_content"]:
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
                        "type": "edit" if "replace" in tool_name.lower() or "Edit" == tool_name else "create",
                        "request_id": request_id,
                    }
                )

    def get_status(self):
        # MISSION CONTROL: Use dict copy to prevent concurrency errors during iteration
        sessions_snapshot = {}
        for rid, s in self.active_sessions.items():
            duration = (datetime.now() - s["start_time"]).total_seconds()
            sessions_snapshot[rid] = {
                "model": s["model"],
                "duration": f"{duration:.1f}s",
                "tools": s["tools"],
                "tokens": s.get("total_tokens", 0)
            }
            
        return {
            "active_count": len(sessions_snapshot),
            "tool_count": self.tool_count,
            "total_tokens": self.total_tokens,
            "total_cost": round(self.total_cost, 4),
            "recent_changes": self.change_log[-15:],
            "active_sessions": sessions_snapshot,
            "model_stats": self.model_stats,
        }


mission_manager = MissionManager()
