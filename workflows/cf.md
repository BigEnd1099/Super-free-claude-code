# Antigravity Launch Workflow

Use this workflow to launch, manage, and test the Antigravity Proxy and its Managed Agents using the `cf.ps1` utility.

## 🚀 Quick Start

To launch the proxy and select a model/agent for Claude Code:

// turbo
```powershell
.\cf.ps1 -Pick
```

## 🛠️ Selection Modes

### 1. Select a Managed Agent
Use an agent's ID to launch Claude Code with specific system instructions and skills.

// turbo
```powershell
.\cf.ps1 -Agent "agent_f3a2b1c0d9e8"
```

### 2. Select a Specific Provider Model
Bypass the default Opus/Sonnet/Haiku mapping and use a specific NVIDIA NIM or OpenRouter model.

// turbo
```powershell
.\cf.ps1 -Model "nvidia_nim/z-ai/glm-5.1"
```

## ⚡ Automation & Batch Mode

For fire-and-forget code generation in automated pipelines:

// turbo
```powershell
.\cf.ps1 -Batch -a agent_f3a2b1c0d9e8 "Implement the feature X"
```

## 📊 Management Utilities

| Flag | Purpose |
| :--- | :--- |
| `-s`, `-Status` | View mission telemetry, uptime, and current engine config. |
| `-l`, `-Logs` | Tail the proxy server logs in real-time. |
| `-r`, `-Reset` | Immediately abort all active missions. |
| `-cfg k:v` | Dynamically toggle settings like `planning:on` or `adversarial:off`. |

## 📊 Dashboard Access
Once the proxy is running, you can monitor traffic and manage skills at:
[http://localhost:8082/ui/](http://localhost:8082/ui/)
