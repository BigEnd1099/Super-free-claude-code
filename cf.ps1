# Usage: .\cf.ps1 [-Pick] [extra claude args...]

param(
    [switch]$Pick,
    [Alias("m")][string]$Model,
    [Alias("a")][string]$Agent
)

$SCRIPT_DIR = $PSScriptRoot
$ENV_FILE = Join-Path $SCRIPT_DIR ".env"
$MODELS_FILE = Join-Path $SCRIPT_DIR "nvidia_nim_models.json"
$AGENTS_FILE = Join-Path $SCRIPT_DIR "agents_db.json"
$DEFAULT_PORT = 8082

# 1. Load basic settings from .env (simple parser)
function Get-EnvValue($key) {
    if (Test-Path $ENV_FILE) {
        $line = Get-Content $ENV_FILE | Where-Object { $_ -match "^\s*${key}\s*=" } | Select-Object -Last 1
        if ($line) {
            $val = ($line -split '=', 2)[1].Trim().Trim('"').Trim("'")
            return $val
        }
    }
    return $null
}

$PORT = Get-EnvValue "PORT"
if (-not $PORT) { $PORT = $DEFAULT_PORT }
$BASE_URL = "http://localhost:$PORT"

$AUTH_TOKEN = Get-EnvValue "ANTHROPIC_AUTH_TOKEN"
if (-not $AUTH_TOKEN) { $AUTH_TOKEN = "freecc" }

$NIM_KEY = Get-EnvValue "NVIDIA_NIM_API_KEY"

# 2. Check if server is running
$serverRunning = $false
try {
    $response = Invoke-WebRequest -Uri "$BASE_URL/health" -UseBasicParsing -ErrorAction SilentlyContinue
    if ($response.StatusCode -eq 200) { $serverRunning = $true }
} catch {}

if (-not $serverRunning) {
    Write-Host "🚀 Starting Claude Code Proxy on port $PORT..." -ForegroundColor Cyan
    # Start the server in a new window
    Start-Process "uv" -ArgumentList "run", "uvicorn", "server:app", "--port", $PORT, "--host", "0.0.0.0" -WindowStyle Minimized
    
    # Wait a moment for it to start
    Write-Host "⏳ Waiting for server to initialize..." -ForegroundColor Gray
    $retries = 10
    while (-not $serverRunning -and $retries -gt 0) {
        Start-Sleep -Seconds 1
        try {
            $response = Invoke-WebRequest -Uri "$BASE_URL/health" -UseBasicParsing -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) { $serverRunning = $true }
        } catch {}
        $retries--
    }
    
    if (-not $serverRunning) {
        Write-Host "❌ Error: Failed to start the proxy server automatically." -ForegroundColor Red
        Write-Host "   Please try running it manually: uv run uvicorn server:app --port $PORT" -ForegroundColor Gray
        exit 1
    }
}

# 3. Model/Agent Selection
$selectionName = $null
$selectionType = "Manual"

if ($Model) {
    $selectionName = $Model
    $selectionType = "Model"
} elseif ($Agent) {
    $selectionName = $Agent
    if (-not $selectionName.StartsWith("agent_")) { $selectionName = "agent_$selectionName" }
    $selectionType = "Agent"
} else {
    # Only show picker if -Pick is passed, OR if no arguments are passed and NVIDIA NIM is NOT the primary provider
    $shouldPick = $Pick.IsPresent
    if (-not $shouldPick -and $args.Count -eq 0 -and [string]::IsNullOrWhiteSpace($NIM_KEY)) {
        $shouldPick = $true
    }

    if ($shouldPick) {
        Write-Host "🔍 Preparing selection..." -ForegroundColor Gray
        
        $options = @()
        
        # Add Models from JSON if exists
        if (Test-Path $MODELS_FILE) {
            $modelsData = Get-Content $MODELS_FILE | ConvertFrom-Json
            foreach ($m in $modelsData.data) {
                $options += [PSCustomObject]@{
                    Type = "Model"
                    Name = "nvidia_nim/$($m.id)"
                    Description = "NVIDIA NIM / Provider Model"
                }
            }
        }
        
        # Add Agents from DB if exists
        if (Test-Path $AGENTS_FILE) {
            $agentsData = Get-Content $AGENTS_FILE | ConvertFrom-Json
            foreach ($agentId in $agentsData.psobject.Properties.Name) {
                $versions = $agentsData.$agentId
                $latest = $versions[-1]
                $options += [PSCustomObject]@{
                    Type = "Agent"
                    Name = $agentId
                    Description = "Managed Agent: $($latest.name)"
                }
            }
        }
        
        if ($options.Count -gt 0) {
            $selection = $options | Out-GridView -Title "Select a Model or Agent for Claude Code" -OutputMode Single
            if ($selection) {
                $selectionName = $selection.Name
                $selectionType = $selection.Type
            }
        }
    }
}

# 4. Configure Environment
$env:ANTHROPIC_BASE_URL = $BASE_URL

if ($selectionName) {
    $env:ANTHROPIC_AUTH_TOKEN = "${AUTH_TOKEN}:$selectionName"
    Write-Host "🚀 Launching Claude with $selectionType: $selectionName..." -ForegroundColor Cyan
} else {
    $env:ANTHROPIC_AUTH_TOKEN = $AUTH_TOKEN
    Write-Host "🚀 Launching Claude..." -ForegroundColor Cyan
}

# 5. Execute
claude @args
