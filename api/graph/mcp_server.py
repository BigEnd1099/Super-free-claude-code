from typing import Any

import networkx as nx
from mcp.server import Server
from mcp.server.fastapi import Context


class GraphMCPServer:
    """Exposes the codebase knowledge graph via MCP tools."""

    def __init__(self, engine: Any):
        self.engine = engine
        self.server = Server("graphify-mcp")
        self._setup_tools()

    def _setup_tools(self):
        @self.server.tool()
        async def query_graph(query: str, ctx: Context) -> dict:
            """Searches the knowledge graph for nodes matching the query."""
            q = query.lower()
            results = [
                node
                for node in self.engine.nodes
                if q in node.get("label", "").lower() or q in node["id"].lower()
            ]
            return {"results": results[:20]}

        @self.server.tool()
        async def get_node_context(node_id: str, ctx: Context) -> dict:
            """Returns the neighbors and connections for a specific node."""
            G = self.engine.get_networkx_graph()
            if node_id not in G:
                return {"error": f"Node {node_id} not found."}

            neighbors = []
            for n in G.neighbors(node_id):
                edge_data = G.get_edge_data(node_id, n)
                neighbors.append(
                    {
                        "id": n,
                        "label": G.nodes[n].get("label", n),
                        "relation": edge_data.get("label", "unknown"),
                    }
                )

            return {"node": {"id": node_id, **G.nodes[node_id]}, "neighbors": neighbors}

        @self.server.tool()
        async def get_shortest_path(source: str, target: str, ctx: Context) -> dict:
            """Finds the shortest architectural path between two components."""
            G = self.engine.get_networkx_graph().to_undirected()
            if source not in G or target not in G:
                return {"error": "Source or target node not found."}

            try:
                path = nx.shortest_path(G, source, target)
                return {"path": path}
            except nx.NetworkXNoPath:
                return {"error": "No path found."}

    def get_router(self):
        return self.server.create_router()
