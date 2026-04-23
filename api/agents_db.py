import json
import os
import time
from typing import Any
from loguru import logger

DB_FILE = "agents_db.json"

class AgentsDB:
    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self):
        if not os.path.exists(self.db_path):
            with open(self.db_path, "w") as f:
                json.dump({}, f)

    def read_db(self) -> dict[str, list[dict[str, Any]]]:
        try:
            if os.path.exists(self.db_path):
                with open(self.db_path, "r") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read agents DB: {e}")
        return {}

    def write_db(self, db: dict[str, list[dict[str, Any]]]):
        try:
            with open(self.db_path, "w") as f:
                json.dump(db, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to write agents DB: {e}")

    def get_all_agents(self) -> list[dict[str, Any]]:
        db = self.read_db()
        agents_list = []
        for agent_id, versions in db.items():
            latest = versions[-1]
            agents_list.append({
                "id": agent_id,
                "name": latest["name"],
                "version": latest["version"],
                "updated_at": latest["updated_at"]
            })
        return agents_list

    def get_agent_versions(self, agent_id: str) -> list[dict[str, Any]] | None:
        db = self.read_db()
        return db.get(agent_id)

    def get_agent(self, agent_id: str) -> dict[str, Any] | None:
        """Get the latest version of an agent by ID."""
        versions = self.get_agent_versions(agent_id)
        return versions[-1] if versions else None

    def create_agent(self, agent_id: str, agent_data: dict[str, Any]) -> dict[str, Any]:
        db = self.read_db()
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        agent = {
            "id": agent_id,
            "type": "agent",
            "name": agent_data.get("name"),
            "model": agent_data.get("model", "claude-3-5-sonnet-20241022"),
            "system": agent_data.get("system"),
            "description": agent_data.get("description"),
            "tools": agent_data.get("tools") or [],
            "skills": agent_data.get("skills") or [],
            "mcp_servers": agent_data.get("mcp_servers") or [],
            "callable_agents": agent_data.get("callable_agents") or [],
            "metadata": agent_data.get("metadata") or {},
            "version": 1,
            "created_at": now,
            "updated_at": now,
            "archived_at": None
        }
        db[agent_id] = [agent]
        self.write_db(db)
        return agent

    def update_agent(self, agent_id: str, update_data: dict[str, Any]) -> dict[str, Any] | None:
        db = self.read_db()
        if agent_id not in db:
            return None
        
        current_agent = db[agent_id][-1]
        
        # Managed Agents Update Semantics:
        # 1. Omitted fields are preserved.
        # 2. Scalar fields (model, system, name, description) are replaced.
        # 3. Array fields (tools, mcp_servers, skills, callable_agents) are fully replaced.
        # 4. Metadata is merged at the key level.
        
        new_agent = current_agent.copy()
        
        # Scalar fields
        for field in ["name", "model", "system", "description"]:
            if field in update_data:
                new_agent[field] = update_data[field]
        
        # Array fields (full replacement)
        for field in ["tools", "mcp_servers", "skills", "callable_agents"]:
            if field in update_data:
                new_agent[field] = update_data[field] or []
        
        # Metadata merge
        if "metadata" in update_data and update_data["metadata"] is not None:
            new_agent["metadata"] = {**current_agent.get("metadata", {}), **update_data["metadata"]}
            # Set to empty string to delete a key (as per spec)
            new_agent["metadata"] = {k: v for k, v in new_agent["metadata"].items() if v != ""}

        # No-op detection
        if self._is_noop(current_agent, new_agent):
            return current_agent

        new_agent["version"] = current_agent["version"] + 1
        new_agent["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        
        db[agent_id].append(new_agent)
        self.write_db(db)
        return new_agent

    def _is_noop(self, old: dict, new: dict) -> bool:
        """Check if any relevant fields changed."""
        fields_to_check = ["name", "model", "system", "description", "tools", "mcp_servers", "skills", "callable_agents", "metadata"]
        for f in fields_to_check:
            if old.get(f) != new.get(f):
                return False
        return True

    def archive_agent(self, agent_id: str) -> dict[str, Any] | None:
        db = self.read_db()
        if agent_id not in db:
            return None
        
        agent = db[agent_id][-1]
        agent["archived_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.write_db(db)
        return agent

# Singleton instance
agents_db = AgentsDB()
