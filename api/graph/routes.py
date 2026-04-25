import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends
from loguru import logger

from api.dependencies import get_settings
from config.settings import Settings

from .engine import GraphifyEngine

router = APIRouter()

# Global engine instance
_engine = None


def get_engine(settings: Settings) -> GraphifyEngine:
    global _engine
    if _engine is None:
        # Check environment variable for root, fallback to CWD
        env_root = os.environ.get("GRAPHIFY_ROOT")
        root = Path(env_root) if env_root and os.path.exists(env_root) else Path.cwd()

        exclude = settings.graphify_exclude_dirs
        _engine = GraphifyEngine(
            root, exclude_dirs=exclude if exclude is not None else []
        )
        # Pre-populate with a single node to avoid infinite scan loops
        _engine.nodes = [
            {"id": "root", "label": "Project Sync Pending", "group": "module"}
        ]
    return _engine


@router.get("/v1/graph/project")
async def get_project_root(settings: Settings = Depends(get_settings)):
    """Get the active project root."""
    engine: GraphifyEngine = get_engine(settings)
    return {"path": str(engine.root_path)}


@router.post("/v1/graph/project")
async def set_project_root(payload: dict, settings: Settings = Depends(get_settings)):
    """Set the active project root for graph scanning."""
    global _engine
    new_path = payload.get("path")
    if new_path and os.path.exists(new_path):
        root = Path(new_path)
        exclude = settings.graphify_exclude_dirs
        # If the path changed, recreate the engine
        if _engine is None or _engine.root_path != root:
            _engine = GraphifyEngine(
                root, exclude_dirs=exclude if exclude is not None else []
            )
            logger.info(f"GRAPHIFY: Project root updated to {root}")

            # Also update skill loader root and reload
            try:
                from api.skills.loader import skill_loader

                skill_loader.root_dir = root
                skill_loader.load_all()
                logger.info(f"SKILLS: Reloaded for new root {root}")
            except Exception as e:
                logger.error(f"SKILLS: Failed to reload for new root: {e}")
        return {"status": "success", "path": str(root)}
    return {"status": "error", "message": "Invalid path"}


@router.get("/v1/graph/scan")
async def scan_codebase(settings: Settings = Depends(get_settings)):
    """Trigger a full scan of the codebase and return the graph data."""
    import anyio

    engine: GraphifyEngine = get_engine(settings)
    try:
        # Ensure we are scanning the latest root
        scan_method: Callable[[], Any] = engine.scan
        data: Any = await anyio.to_thread.run_sync(scan_method)
        logger.info(
            f"GRAPHIFY: Scan completed for {engine.root_path} with {len(data['nodes'])} nodes."
        )
        return data
    except Exception as e:
        logger.error(f"GRAPHIFY: Scan failed: {e}")
        return {"nodes": [], "edges": [], "error": str(e)}


@router.get("/v1/graph/data")
async def get_graph_data(settings: Settings = Depends(get_settings)):
    """Returns the most recent graph data without rescanning."""
    engine: GraphifyEngine = get_engine(settings)
    if not engine.nodes:
        return await scan_codebase(settings)
    return {"nodes": engine.nodes, "edges": engine.edges}


@router.get("/v1/graph/report")
async def get_graph_report(settings: Settings = Depends(get_settings)):
    """Generates and returns a structural report of the graph."""
    import anyio

    from .report_generator import GraphReportGenerator

    engine: GraphifyEngine = get_engine(settings)
    if not engine.nodes:
        await scan_codebase(settings)

    generator = GraphReportGenerator(engine.get_networkx_graph(), engine.root_path)
    generate_method: Callable[[], Any] = generator.generate
    report_content: Any = await anyio.to_thread.run_sync(generate_method)
    return {"report": report_content}
