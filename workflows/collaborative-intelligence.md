# Collaborative Intelligence Workflow (Antigravity + Claude Code)

This workflow defines the "Architect & Executor" protocol for seamless collaboration between Antigravity (the Architect) and Claude Code (the Executor).

## 🛡️ Role Definitions

| AI System | Role | Primary Responsibility |
| :--- | :--- | :--- |
| **Antigravity** | **Architect** | Environment config, agent design, mission planning, and batch delegation. |
| **Claude Code** | **Executor** | Deep code implementation, terminal execution, and multi-file refactoring. |

---

## 🛰️ Collaboration Protocol

### 1. The Mission Briefing
The Architect prepares the "Neural Context" and selects an agent.

// turbo
```powershell
# Check current status
.\cf.ps1 -s
```

### 2. Delegation Phase (Manual or Automated)

**Manual Handoff:**
Launch Claude Code and paste the mission brief.
// turbo
```powershell
.\cf.ps1 -Pick
```

**Automated Delegation (Batch):**
The Architect fires a headless command for specific implementation.
// turbo
```powershell
.\cf.ps1 -Batch -a agent_id "Instruction"
```

### 3. Real-Time Oversight (Mission Control)
While Claude Code is executing, monitor via `cf -s` or the Super FCC Dashboard:
- **Visibility**: Watch the **Neural Change Log** as files are being modified in real-time.
- **Management**: If the AI goes off-track, use `.\cf.ps1 -r` to immediately stop all orchestration.

### 4. Validation Loop
Once Claude Code finishes:
1.  Verify changes via `cf "run tests"`.
2.  Antigravity performs a **Security & Architecture Review**.

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
1.  **Antigravity** must never perform deep multi-file edits while Claude Code is active.
2.  **Claude Code** must respect the `config/settings.py` patterns.
3.  **Antigravity** is the source of truth for `agents_db.json`.
