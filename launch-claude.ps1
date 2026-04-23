# Claude Ultimate Antigravity Launcher
# This script ensures the environment is set correctly and launches Claude Code

$env:ANTHROPIC_BASE_URL = "http://localhost:8082"
$env:ANTHROPIC_AUTH_TOKEN = "freecc"

Write-Host "🚀 Launching Claude with Antigravity Proxy..." -ForegroundColor Cyan
claude @args
