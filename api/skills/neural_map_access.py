from typing import Any, ClassVar

import httpx
from loguru import logger

from api.skills.base import Skill


class NeuralMapAccessSkill(Skill):
    """Provides agents with full read access to the project's Neural Map (architectural dependencies)."""

    name = "neural_map_access"
    description = (
        "Query the project's Neural Map to understand file dependencies, class structures, "
        "and architectural patterns. Returns a list of nodes and edges representing the codebase."
    )
    input_schema: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "query_type": {
                "type": "string",
                "enum": ["full_graph", "find_node", "neighborhood"],
                "description": "Type of query: 'full_graph' for everything, 'find_node' to find a specific file/class, 'neighborhood' to find connections.",
            },
            "target_id": {
                "type": "string",
                "description": "The ID of the node to find or explore (required for 'find_node' and 'neighborhood').",
            },
        },
        "required": ["query_type"],
    }

    async def run(
        self, query_type: str, target_id: str | None = None
    ) -> dict[str, Any]:
        # We can query our own internal API
        # Since we are running in the same process/server context (usually),
        # we could call the engine directly, but using the API is cleaner and ensures consistency.

        # We need to know our own base URL. We can assume localhost:8082 or get from environment.
        import os

        port = os.environ.get("PORT", "8082")
        base_url = f"http://localhost:{port}/v1/graph/data"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Add API key if needed
                headers = {}
                auth_token = os.environ.get("ANTHROPIC_AUTH_TOKEN", "")
                if auth_token:
                    headers["x-api-key"] = auth_token.split(":")[0]

                response = await client.get(base_url, headers=headers)
                if response.status_code != 200:
                    return {
                        "error": f"Failed to fetch graph data: {response.status_code}"
                    }

                data = response.json()

                if query_type == "full_graph":
                    # Summary of graph size to avoid token blowout
                    return {
                        "node_count": len(data.get("nodes", [])),
                        "edge_count": len(data.get("edges", [])),
                        "nodes_sample": data.get("nodes", [])[
                            :50
                        ],  # Sample to avoid overloading
                        "message": "Full graph data retrieved. Returning first 50 nodes as sample. Use 'find_node' for specific details.",
                    }

                elif query_type == "find_node":
                    if not target_id:
                        return {"error": "target_id is required for find_node"}

                    found = [
                        n
                        for n in data.get("nodes", [])
                        if target_id.lower() in n.get("id", "").lower()
                        or target_id.lower() in n.get("label", "").lower()
                    ]
                    return {"matches": found}

                elif query_type == "neighborhood":
                    if not target_id:
                        return {"error": "target_id is required for neighborhood"}

                    nodes = data.get("nodes", [])
                    edges = data.get("edges", [])

                    # Find the node
                    center = next((n for n in nodes if n["id"] == target_id), None)
                    if not center:
                        return {"error": f"Node '{target_id}' not found."}

                    # Find connected edges
                    connected_edges = [
                        e
                        for e in edges
                        if e["from"] == target_id or e["to"] == target_id
                    ]
                    neighbor_ids = set()
                    for e in connected_edges:
                        neighbor_ids.add(e["from"])
                        neighbor_ids.add(e["to"])

                    neighbor_nodes = [n for n in nodes if n["id"] in neighbor_ids]

                    return {
                        "center": center,
                        "neighbors": neighbor_nodes,
                        "edges": connected_edges,
                    }

                return {"error": "Invalid query_type"}

        except Exception as e:
            logger.error(f"NeuralMapAccessSkill failed: {e}")
            return {"error": str(e)}
