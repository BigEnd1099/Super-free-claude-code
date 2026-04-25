# Architect → Executor Automation Protocol

This protocol defines the autonomous delegation pipeline where Antigravity (the Architect) utilizes the `cf` utility in **Batch Mode** to drive code changes via Claude Code (the Executor).

## 🛰️ The Batch Pipeline

When Antigravity needs to delegate a task, it follows this sequence:

### 1. Planning & Agent Selection
Antigravity analyzes the requirement and selects the most appropriate **Managed Agent** (e.g., `agent_f3a2b1c0d9e8` for Systems Engineering).

### 2. Formulating the Delegate Command
Antigravity constructs a command using the `-Batch` flag to suppress interactive blocks.

// turbo
```powershell
.\cf.ps1 -Batch -a agent_f3a2b1c0d9e8 "Implement the logging middleware in api/app.py"
```

### 3. Execution (Executor Phase)
Claude Code launches in headless mode:
- `--dangerously-skip-permissions` is injected to prevent "Antigravity Architect" from being asked for permission by "Claude Code Executor".
- `--output-format stream-json` ensures the result is machine-readable if captured.

### 4. Monitoring (Mission Control)
Antigravity can monitor progress via:
- **Telemetry API**: `GET /v1/mission/status` (via `cf -s`)
- **Dashboard**: `http://localhost:8082/ui/`

## 🛡️ Safety Constraints

1. **Non-Overlapping Edits**: The Architect should not modify files currently being handled by the Executor to avoid conflicts.
2. **Atomic Tasks**: Break large refactors into discrete `cf -Batch` calls.
3. **Validation**: Always run CI checks (`cf "run tests"`) after an automated batch run.

## ⚡ Multi-Agent Swarms
Antigravity can parallelize work by spinning up multiple batch sessions in separate terminals:

```powershell
# Logic & Tests in parallel
Start-Process powershell -ArgumentList ".\cf.ps1 -Batch -a agent_logic 'Fix the bug'"
Start-Process powershell -ArgumentList ".\cf.ps1 -Batch -a agent_tests 'Add test coverage'"
```
