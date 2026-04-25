---
description: Automated Agentic Workflow for Antigravity Proxy Management
---

Here is the upgraded workflow, explicitly tailored to integrate Antigravity as the proxy manager for Anthropic's Claude Code CLI. I've added the necessary environment routing, lifecycle management, and specific commands to bridge the proxy’s intelligence layers with Claude Code's native operations. 

***

# 🛰️ Antigravity x Claude Code: Automated Mission Workflow

Use this workflow to automate the deployment, tuning, and monitoring of the Antigravity Proxy while it drives the **Claude Code** CLI. As an agent, follow these procedures to ensure Claude Code routes through the proxy and leverages its augmented intelligence features.

---

Set-Alias cf .\cf.ps1

---

## 🔌 Procedure: Pre-Flight Routing
Run this procedure to intercept Claude Code's traffic and route it through the local Antigravity proxy.

### Launch Claude with default .env settings.
// turbo
```
cl
```

---

## 🚀 Procedure: Initial Deployment
Initialize the proxy server and launch the Claude Code environment for the current mission.

### Launch Proxy with Interactive Selection
Start the backend proxy and select the underlying model/agent to power Claude Code.
// turbo
```powershell
cf -m <model>
```

### Direct Agent Routing (Specialized)
If the task requires a specific persona for Claude Code's backend, launch with a predefined agent.
// turbo
```powershell
cf -Agent "agent_id_here"
```

---

## 🧠 Procedure: Intelligence Augmentation
Run these commands in a separate terminal to dynamically adjust the proxy's intelligence layers while Claude Code is actively processing tasks.

### Enable OmX Planning Mode
Use this when Claude Code needs to make complex architectural decisions or structural repository planning.
// turbo
```powershell
cf -Settings planning:on
```

### Enable Parseltongue (Adversarial Mode)
Use this if Claude Code's operations or code generations are being blocked by provider-side safety filters.
// turbo
```powershell
cf -Settings adversarial:on
```

### Configure Neural Thinking
Toggle the visibility of thinking blocks to optimize Claude Code's response speed or to audit its reasoning.
// turbo
```powershell
cf -Settings thinking:on
```

---

## 📊 Procedure: Telemetry & Monitoring
Execute these steps to verify mission health, monitor Claude Code's token usage, and track system performance.

### Fetch Proxy Mission Status
Retrieve real-time metrics on active sessions, tokens routed through the proxy, and file changes.
// turbo
```powershell
cf -Status
```

### Diagnostics: Tail Logs
Use this if Claude Code encounters connection errors, `500 Internal Server Errors`, or unexpected provider behavior.
// turbo
```powershell
cf -Logs
```

---

## 🛠️ Procedure: System Maintenance
Execute these commands to cleanly shut down or reset the workspace.

### Clear Proxy Mission Sessions
Aborts all active backend proxy sessions and resets the mission manager.
// turbo
```powershell
Invoke-RestMethod -Uri "http://localhost:8082/v1/mission/stop" -Method Post -Headers @{ "x-api-key" = "freecc" }
```

### Flush Claude Code Context
Use this to wipe Claude Code's internal memory if the context window gets too heavy or if starting a new, distinct task.
// turbo
```powershell
claude /clear
```