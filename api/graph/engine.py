import importlib
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import networkx as nx
from loguru import logger


@dataclass
class LanguageConfig:
    ts_module: str
    ts_language_fn: str = "language"
    class_types: frozenset = frozenset()
    function_types: frozenset = frozenset()
    import_types: frozenset = frozenset()
    name_field: str = "name"
    name_fallback_child_types: tuple = ()


_CONFIGS = {
    ".py": LanguageConfig(
        ts_module="tree_sitter_python",
        class_types=frozenset({"class_definition"}),
        function_types=frozenset({"function_definition"}),
        import_types=frozenset({"import_statement", "import_from_statement"}),
    ),
    ".js": LanguageConfig(
        ts_module="tree_sitter_javascript",
        class_types=frozenset({"class_declaration"}),
        function_types=frozenset({"function_declaration", "method_definition"}),
        import_types=frozenset({"import_statement"}),
    ),
    ".ts": LanguageConfig(
        ts_module="tree_sitter_typescript",
        ts_language_fn="language_typescript",
        class_types=frozenset({"class_declaration"}),
        function_types=frozenset({"function_declaration", "method_definition"}),
        import_types=frozenset({"import_statement"}),
    ),
    ".tsx": LanguageConfig(
        ts_module="tree_sitter_typescript",
        ts_language_fn="language_tsx",
        class_types=frozenset({"class_declaration"}),
        function_types=frozenset({"function_declaration", "method_definition"}),
        import_types=frozenset({"import_statement"}),
    ),
    ".go": LanguageConfig(
        ts_module="tree_sitter_go",
        class_types=frozenset({"type_declaration"}),
        function_types=frozenset({"function_declaration", "method_declaration"}),
        import_types=frozenset({"import_declaration"}),
    ),
    ".rs": LanguageConfig(
        ts_module="tree_sitter_rust",
        class_types=frozenset({"struct_item", "enum_item", "trait_item"}),
        function_types=frozenset({"function_item"}),
        import_types=frozenset({"use_declaration"}),
    ),
    ".cs": LanguageConfig(
        ts_module="tree_sitter_c_sharp",
        class_types=frozenset(
            {"class_declaration", "struct_declaration", "interface_declaration"}
        ),
        function_types=frozenset({"method_declaration", "constructor_declaration"}),
        import_types=frozenset({"using_directive"}),
    ),
}


class GraphifyEngine:
    """Advanced AST engine with multi-language support and community detection."""

    def __init__(self, root_path: Path, exclude_dirs: list[str] | None = None):
        self.root_path = root_path
        self.exclude_dirs = exclude_dirs or [
            ".venv",
            "__pycache__",
            ".git",
            "static",
            "node_modules",
            "dist",
            "build",
            "bin",
            "obj",
            ".vs",
            "Library",
            "Temp",
            "Logs",
            "Packages",
            "Artifacts",
            "MISSION_REPORTS",
            "MISSION_JOURNAL",
            "references",
            "frontend",
            "dist",
            "out",
            ".vs",
            ".idea",
        ]
        self.nodes: list[dict] = []
        self.edges: list[dict] = []
        self._seen_nodes: set[str] = set()
        self.max_nodes = 5000  # Safety limit for large projects

    def _make_id(self, *parts: str) -> str:
        """Build a stable node ID."""
        combined = "_".join(p.strip("_.") for p in parts if p)
        cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", combined)
        return cleaned.strip("_").lower()

    def _read_text(self, node, source: bytes) -> str:
        return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")

    def scan(self) -> dict[str, Any]:
        """Scans the project and builds the graph."""
        self.nodes = []
        self.edges = []
        self._seen_nodes = set()

        logger.info(
            f"GRAPHIFY: Starting advanced multi-language scan of {self.root_path}"
        )

        for root, dirs, files in os.walk(self.root_path):
            if len(self.nodes) > self.max_nodes:
                logger.warning(
                    f"GRAPHIFY: Reached max nodes ({self.max_nodes}). Truncating scan."
                )
                break

            # Filter excluded directories
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]

            # Add directory nodes
            rel_root = str(Path(root).relative_to(self.root_path))
            if rel_root != ".":
                dir_id = self._make_id("dir", rel_root)
                self._add_node(dir_id, label=rel_root, group="directory", level=0)

                # Link to parent directory
                parent = str(Path(rel_root).parent)
                if parent != ".":
                    parent_id = self._make_id("dir", parent)
                    self._add_edge(parent_id, dir_id, label="contains")

            for file in files:
                file_path = Path(root) / file
                ext = file_path.suffix

                try:
                    fsize = os.path.getsize(file_path)
                except OSError:
                    fsize = 1000

                node_size = 10 + (math.log10(max(1, fsize)) * 5)
                file_nid = self._make_id(rel_root, file)

                self._add_node(
                    file_nid,
                    label=file,
                    group="module" if ext in _CONFIGS else "file",
                    path=str(file_path.relative_to(self.root_path)),
                    size=node_size,
                    level=1,
                )

                if rel_root != ".":
                    dir_id = self._make_id("dir", rel_root)
                    self._add_edge(dir_id, file_nid, label="contains")

                if ext in _CONFIGS:
                    self._process_file(file_path, _CONFIGS[ext], rel_root, file_nid)

        self._apply_clustering()
        return {"nodes": self.nodes, "edges": self.edges}

    def _process_file(
        self, file_path: Path, config: LanguageConfig, rel_root: str, file_nid: str
    ):
        """Parses a file using tree-sitter."""
        rel_path = str(file_path.relative_to(self.root_path))

        try:
            from tree_sitter import Language, Parser

            mod = importlib.import_module(config.ts_module)
            lang_fn = getattr(mod, config.ts_language_fn)
            language = Language(lang_fn())
            parser = Parser(language)

            source = file_path.read_bytes()
            tree = parser.parse(source)

            self._walk(tree.root_node, source, config, file_nid, rel_path)

        except Exception as e:
            logger.warning(f"GRAPHIFY: Failed to parse {rel_path}: {e}")

    def _walk(
        self,
        node: Any,
        source: bytes,
        config: LanguageConfig,
        file_nid: str,
        rel_path: str,
    ):
        """Recursive AST walk."""
        t = node.type
        line = node.start_point[0] + 1

        if t in config.class_types:
            name_node = node.child_by_field_name(config.name_field)
            if name_node:
                name = self._read_text(name_node, source)
                class_nid = self._make_id(rel_path, name)
                self._add_node(
                    class_nid,
                    label=name,
                    group="class",
                    path=rel_path,
                    line=line,
                    level=2,
                )
                self._add_edge(
                    file_nid, class_nid, label="contains", confidence="EXTRACTED"
                )

        elif t in config.function_types:
            name_node = node.child_by_field_name(config.name_field)
            if name_node:
                name = self._read_text(name_node, source)
                func_nid = self._make_id(rel_path, name)
                self._add_node(
                    func_nid,
                    label=name,
                    group="function",
                    path=rel_path,
                    line=line,
                    level=3,
                )
                self._add_edge(
                    file_nid, func_nid, label="contains", confidence="EXTRACTED"
                )

        elif t in config.import_types:
            import_text = self._read_text(node, source).strip()
            if import_text:
                import_id = self._make_id(rel_path, f"import_{line}")
                self._add_node(
                    import_id,
                    label=import_text,
                    group="import",
                    path=rel_path,
                    line=line,
                    level=4,
                )
                self._add_edge(file_nid, import_id, label="imports")

        if t == "comment":
            comment_text = self._read_text(node, source)
            if any(
                marker in comment_text.upper()
                for marker in ["TODO", "HACK", "NOTE", "FIXME"]
            ):
                rat_id = self._make_id(rel_path, f"rationale_{line}")
                self._add_node(
                    rat_id,
                    label=comment_text.strip("# "),
                    group="rationale",
                    path=rel_path,
                    line=line,
                    level=5,
                )
                self._add_edge(file_nid, rat_id, label="has_rationale")

        for child in node.children:
            self._walk(child, source, config, file_nid, rel_path)

    def _add_node(self, node_id: str, **kwargs: Any):
        if node_id not in self._seen_nodes:
            node = {"id": node_id}
            node.update(kwargs)
            self.nodes.append(node)
            self._seen_nodes.add(node_id)

    def _add_edge(self, source: str, target: str, label: str = "", **kwargs: Any):
        if source == target:
            return

        edge = {"from": source, "to": target, "label": label}
        edge.update(kwargs)
        if edge not in self.edges:
            self.edges.append(edge)

    def _apply_clustering(self):
        """Applies community detection to the graph."""
        if not self.nodes:
            return

        if len(self.nodes) > 1000:
            logger.info("GRAPHIFY: Graph too large for real-time clustering. Skipping.")
            return

        G = nx.Graph()
        for node in self.nodes:
            G.add_node(node["id"])
        for edge in self.edges:
            G.add_edge(edge["from"], edge["to"])

        try:
            communities = nx.community.louvain_communities(G, seed=42)
            node_to_comm = {}
            for i, comm in enumerate(communities):
                for node_id in comm:
                    node_to_comm[node_id] = i

            for node in self.nodes:
                node["community"] = node_to_comm.get(node["id"], -1)

            logger.info(f"GRAPHIFY: Detected {len(communities)} communities.")
        except Exception as e:
            logger.warning(f"GRAPHIFY: Clustering failed: {e}")

    def get_networkx_graph(self) -> nx.Graph:
        """Returns the graph as a NetworkX object."""
        G = nx.DiGraph()
        for node in self.nodes:
            G.add_node(node["id"], **{k: v for k, v in node.items() if k != "id"})
        for edge in self.edges:
            G.add_edge(
                edge["from"],
                edge["to"],
                **{k: v for k, v in edge.items() if k not in ["from", "to"]},
            )
        return G
