from typing import List, Dict, Any
from loguru import logger

class ForensicAnalyzer:
    """Analyzes failed sessions to identify root causes."""

    def analyze(self, session_id: str, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Performs forensic analysis on session events."""
        logger.info(f"FORENSICS: Analyzing session {session_id}")
        
        analysis = {
            "session_id": session_id,
            "root_cause": "unknown",
            "confidence": 0.0,
            "recommendation": "none"
        }

        # Look for common failure patterns
        for event in reversed(events):
            # 1. Rate Limit Hit
            if event.get("type") == "error" and "rate limit" in str(event.get("message", "")).lower():
                analysis["root_cause"] = "rate_limit_exceeded"
                analysis["confidence"] = 0.9
                analysis["recommendation"] = "SWITCH_TO_FLASH"
                break
            
            # 2. Tool Failure Loop
            if event.get("type") == "tool_result" and event.get("status") == "error":
                analysis["root_cause"] = "persistent_tool_failure"
                analysis["confidence"] = 0.7
                analysis["recommendation"] = "INJECT_DEBUG_PROMPT"
                break

        return analysis

forensic_analyzer = ForensicAnalyzer()
