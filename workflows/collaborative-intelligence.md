# Collaborative Intelligence Workflow (Antigravity + Claude Code)

This workflow defines the "Architect & Executor" protocol for seamless collaboration between Antigravity (this session) and Claude Code (the CLI).

## 🛡️ Role Definitions

| AI System | Role | Primary Responsibility |
| :--- | :--- | :--- |
| **Antigravity** | **Architect** | Environment config, agent design, skill discovery, and mission planning. |
| **Claude Code** | **Executor** | Deep code implementation, terminal execution, and multi-file refactoring. |

---

## 🛰️ Collaboration Protocol

### 1. The Mission Briefing
Before launching Claude Code, Antigravity prepares the "Neural Context".

// turbo
```powershell
# Antigravity prepares the agent and outputs a mission summary
.\cf.ps1 -Pick
```

### 2. Context Handoff
Antigravity will provide a **Mission Token**. Paste this into your Claude Code prompt:
> "I am working with Antigravity Architect. Current goal: [Architecture Plan]. Please implement the changes following the [Design Tokens]."

### 3. Execution Phase
Run Claude Code using the mission-specific environment:

// turbo
```powershell
# Launch with the Architect's environment
.\cf.ps1 "Implement Phase 1 of the architecture plan"
```

### 4. Real-Time Oversight (Mission Control)
While Claude Code is executing, open the Antigravity Dashboard:
- **Tab**: `Mission Control`
- **Visibility**: Watch the **Neural Change Log** as files are being modified in real-time.
- **Management**: If the AI goes off-track, use the **ABORT ALL MISSIONS** button to immediately stop the orchestration.

### 5. Validation Loop
Once Claude Code finishes:
1.  Come back to Antigravity.
2.  Provide the `logs/` or `diffs` generated.
3.  Antigravity will perform a **Security & Architecture Review**.

---

## ⚡ Multi-Agent Swarm (Advanced)
You can launch multiple Claude Code sessions with different **Managed Agents** simultaneously:

// turbo
```powershell
# Terminal 1: Design Agent
.\cf.ps1 -Agent "agent_design" "Refine the CSS tokens"

# Terminal 2: Logic Agent
.\cf.ps1 -Agent "agent_logic" "Fix the API race condition"
```

---

## 📝 Rules for Both AIs
1.  **Antigravity** must never perform deep multi-file edits while Claude Code is active to avoid merge conflicts.
2.  **Claude Code** must respect the `config/settings.py` patterns established by Antigravity.
3.  **Antigravity** is the source of truth for `agents_db.json`.
