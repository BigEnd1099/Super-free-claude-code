---
description: for super cloude free antigravity
---

# Antigravity Launch Workflow

Use this workflow to launch, manage, and test the Antigravity Proxy and its Managed Agents using the `cf.ps1` utility.

## 🚀 Quick Start

To launch the proxy and select a model/agent for Claude Code:

// turbo
```powershell
cf -Pick
```

## 🛠️ Selection Modes

### 1. Select a Managed Agent
Use an agent's ID to launch Claude Code with specific system instructions and skills.

// turbo
```powershell
cf -Agent "agent_6143b26978e7"
```

### 2. Select a Specific Provider Model
Bypass the default Opus/Sonnet/Haiku mapping and use a specific NVIDIA NIM or OpenRouter model.

// turbo
```powershell
cf -Model "nvidia_nim/z-ai/glm4.7"
```

## 🧪 Testing Integration

To verify the proxy connection with a one-off command:

// turbo
```powershell
cf "Hello, identify yourself" -p --bare
```

## 📊 Dashboard Access
Once the proxy is running, you can monitor traffic and manage skills at:
[http://localhost:8082/ui/](http://localhost:8082/ui/)

## 📝 Troubleshooting
- **Port Conflict**: If port 8082 is busy, update `PORT` in your `.env` file.
- **Auth Error**: Ensure `ANTHROPIC_AUTH_TOKEN` matches in your `.env` and the Claude Code settings.
- **Model Missing**: Check `nvidia_nim_models.json` to ensure your provider model is discovered.
