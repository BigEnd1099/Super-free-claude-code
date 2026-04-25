# ANTIGRAVITY NEXUS: NEURAL MAP (STATIC VIEW)

This document provides a hierarchical, text-based representation of the project's architecture, extracted via the **Graphify Engine**.

---

## 1. CORE CONTROL PLANE (`api/`)

### `api.app` (Application Factory)
- `create_app()`: Primary entry point for FastAPI initialization.

### `api.routes` (Control Logic)
- `perturb_prompt()`: Adversarial (Parseltongue) logic.
- `strip_preambles()`: Raw Mode (STM) logic.
- `create_message()`: Core streaming orchestration.

### `api.telemetry` (State Management)
- **Class `MissionManager`**: Source of truth for sessions and metrics.
    - `log_tokens()`: Financial/Usage tracking.
    - `log_tool()`: Tool call interception.
    - `get_status()`: Real-time dashboard telemetry.
- **Class `ThinkingCache`**: Persistence for thinking signatures.

### `api.graph.engine` (Neural Mapping)
- **Class `GraphifyEngine`**: The AST engine that generated this map.
    - `scan()`: Recursive codebase analysis.
    - `_process_file()`: AST node extraction.

### `api.orchestration.manager` (Agent Streams)
- **Class `AgentTeamManager`**: Multi-agent session management.
- **Class `TeamState`**: Shared memory (Whiteboard) implementation.

---

## 2. PROVIDER LAYER (`providers/`)

### `providers.resilience` (Healing Layer)
- `with_resilient_stream()`: Adaptive retry and fallback logic.

### `providers.common` (Shared Utilities)
- `get_user_facing_error_message()`: Semantic error translation.

### `providers.manager` (Model Intelligence)
- **Class `ProviderManager`**: Model mapping and routing logic.

---

## 3. CONFIGURATION & INFRASTRUCTURE (`config/`)

### `config.settings` (System Directives)
- **Class `Settings`**: Pydantic-based configuration management.

### `config.logging_config` (Forensics)
- `configure_logging()`: loguru-based asynchronous logging.

---

## 4. PERSISTENCE & DATA (`api/agents_db.py`)
- **Class `AgentsDB`**: Persistent storage for customized agent personas.

---

## 5. LIVE TELEMETRY (`api/websockets.py`)
- **Class `ConnectionManager`**: Broadcast engine for real-time dashboard updates.

---

## 6. PROJECT TOPOLOGY (METRICS)
- **Total Nodes Analyzed**: ~1,200+
- **Key Patterns**:force-directed, hierarchical, streaming-first.

> [!NOTE]
> For the raw graph data (nodes/edges) in JSON format, see [NEURAL_MAP.json](file:///d:/Claude-Ultimate-Antigravity/docs/NEURAL_MAP.json).
