# Advanced_Analytics_Dashboard_Roadmap.md

## 1. Architecture Review
The **Advanced Analytics Dashboard** will be integrated as a primary intelligence module within the Antigravity Proxy (Super FCC). It aims to provide real-time and historical visibility into token consumption, cost distribution, and agent performance.

### 🛰️ Integration Points
- **Backend (API)**: New analytics engine in `api/analytics.py` to interface with the SQLite telemetry database.
- **Middleware**: Enhanced logging in `MissionManager` to capture per-mission ROI and performance metrics.
- **Frontend**: A dedicated "Analytics" view in the WebUI (`static/ui/`).

### 📦 New Dependencies
- **Chart.js**: For rendering interactive time-series and distribution charts.
- **SQLAlchemy/SQLModel Extension**: For complex aggregation queries (average tokens/sec, cost per agent).
- **Date-utils**: For handling timezone-aware mission history.

---

## 2. Step-by-Step Execution Plan (For Claude Code)

### Phase 0: Environment & Schema Preparation
- [ ] **Task 0.1**: Verify `TelemetryRecord` in `api/models/` includes `cost`, `duration`, and `session_id`.
- [ ] **Task 0.2**: Initialize `api/analytics.py` with base aggregation functions using `sqlmodel`.
- [ ] **Task 0.3**: Update `pyproject.toml` if any new visualization libraries are needed.

### Phase 1: Data Aggregation Layer
- [ ] **Task 1.1**: Implement `GET /v1/analytics/summary` (Total Tokens, Total Cost, Uptime, Active Agents).
- [ ] **Task 1.2**: Implement `GET /v1/analytics/models` (Usage breakdown by provider: NVIDIA NIM, OpenRouter, Anthropic).
- [ ] **Task 1.3**: Implement `GET /v1/analytics/missions` (Success rate and token efficiency per mission type).

### Phase 2: WebUI Component Implementation
- [ ] **Task 2.1**: Create `static/ui/components/AnalyticsPanel.js` using Chart.js.
- [ ] **Task 2.2**: Implement a "Token Burn Rate" line chart and a "Model Share" doughnut chart.
- [ ] **Task 2.3**: Update `static/index.html` to include the "Advanced Analytics" tab in the main navigation.

### Phase 3: Brand Alignment & UX
- [ ] **Task 3.1**: Style the charts using CSS variables from `brand_guidelines.md` (Glow effects, neon accents, dark mode backgrounds).
- [ ] **Task 3.2**: Add tooltips to charts showing precise mission IDs and token counts on hover.

---

## 3. Testing & MCP Handoff

### 🧪 Validation Protocol
- **Backend**: Run `uv run pytest tests/test_analytics.py` to ensure JSON responses match the database state.
- **Frontend**: Use the `browser_subagent` to verify the charts render without layout shifts.

### 🤖 Claude Code Instructions (MCP)
1. **Bootstrap Tests**: "Claude, use the `run_command` tool to create a baseline test suite in `tests/test_analytics.py` that mocks the `mission_manager` and checks if `/v1/analytics/summary` returns valid non-zero values."
2. **UI Audit**: "Use the `browser_subagent` to navigate to the new Analytics tab. Verify that the Chart.js canvas is responsive and that no 'Chart not found' errors appear in the console logs."
3. **Stress Test**: "Simulate 10 high-frequency API calls and check the `server.log` (via `cf -l`) for any database locking issues or query performance bottlenecks."
