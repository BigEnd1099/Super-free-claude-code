# Usage: .\cf.ps1 [-Pick] [-Model model] [-Agent agent] [-Logs] [-Status] [-Reset] [-Settings key:val] [-Help] [extra claude args...]

$SCRIPT_DIR = $PSScriptRoot
$ENV_FILE = Join-Path $SCRIPT_DIR ".env"
$MODELS_FILE = Join-Path $SCRIPT_DIR "nvidia_nim_models.json"
$AGENTS_FILE = Join-Path $SCRIPT_DIR "agents_db.json"
$LOG_FILE = Join-Path $SCRIPT_DIR "server.log"
$DEFAULT_PORT = 8082

# 0. Manual Argument Parsing (to avoid clashing with Claude's -p, -v, etc.)
$Selection = $false
$Model = $null
$Agent = $null
$ShowLogs = $false
$ShowStatus = $false
$ResetMissions = $false
$ShowHelp = $false
$UpdateSettings = $null
$ClaudeArgs = @()

$i = 0
while ($i -lt $args.Count) {
    $arg = $args[$i]
    if ($arg -match "^-(Pick|Selection|Select)$") {
        $Selection = $true
    } elseif ($arg -match "^-(Model|m)$") {
        $i++
        if ($i -lt $args.Count) { $Model = $args[$i] }
    } elseif ($arg -match "^-(Agent|a)$") {
        $i++
        if ($i -lt $args.Count) { $Agent = $args[$i] }
    } elseif ($arg -match "^-(Logs|l)$") {
        $ShowLogs = $true
    } elseif ($arg -match "^-(Status|s)$") {
        $ShowStatus = $true
    } elseif ($arg -match "^-(Reset|r)$") {
        $ResetMissions = $true
    } elseif ($arg -match "^-(Help|h|\?)$") {
        $ShowHelp = $true
    } elseif ($arg -match "^-(Settings|cfg)$") {
        $i++
        if ($i -lt $args.Count) { $UpdateSettings = $args[$i] }
    } else {
        $ClaudeArgs += $arg
    }
    $i++
}

if ($ShowHelp) {
    Write-Host "`n🛰️  ANTIGRAVITY PROXY - POWER LAUNCHER" -ForegroundColor Cyan
    Write-Host "Usage: cf [options] [claude_args]`n" -ForegroundColor White
    Write-Host "OPTIONS:" -ForegroundColor Gray
    Write-Host "  -Pick, -Select     Open interactive GUI to select model or agent."
    Write-Host "  -m, -Model <id>    Directly use a specific provider model."
    Write-Host "  -a, -Agent <id>    Directly use a specific Managed Agent persona."
    Write-Host "  -s, -Status        Fetch real-time mission metrics and token usage."
    Write-Host "  -l, -Logs          Tail the proxy server logs."
    Write-Host "  -r, -Reset         Abort all active proxy sessions and reset mission manager."
    Write-Host "  -cfg <key>:<val>   Update dynamic settings (e.g., -cfg planning:on)."
    Write-Host "  -h, -Help          Show this help menu.`n"
    Write-Host "INTELLIGENCE SETTINGS:" -ForegroundColor Gray
    Write-Host "  planning:on/off    Enable OmX Structured Architectural Planning."
    Write-Host "  adversarial:on/off Enable Parseltongue Input Perturbation."
    Write-Host "  thinking:on/off    Enable Neural Thinking block visibility."
    Write-Host "  raw_mode:on/off    Enable STM (Semantic Output Normalization).`n"
    exit 0
}

# 1. Load basic settings from .env
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
    Write-Host "[*] Starting Claude Code Proxy on port $PORT..." -ForegroundColor Cyan
    Start-Process "uv" -ArgumentList "run", "uvicorn", "server:app", "--port", $PORT, "--host", "0.0.0.0", "--reload" -WindowStyle Minimized
    Write-Host "[...] Waiting for server to initialize..." -ForegroundColor Gray
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
        Write-Host "[!] Error: Failed to start the proxy server automatically." -ForegroundColor Red
        exit 1
    }
}

# 3. Handle Utilities (Logs, Status, Settings, Reset)
if ($ShowLogs) {
    if (Test-Path $LOG_FILE) {
        Write-Host "[*] Tailing proxy logs (Ctrl+C to stop)..." -ForegroundColor Cyan
        Get-Content $LOG_FILE -Wait -Tail 20
    } else {
        Write-Host "[!] Error: Log file not found at $LOG_FILE" -ForegroundColor Red
    }
    exit 0
}

if ($ResetMissions) {
    try {
        Invoke-RestMethod -Uri "$BASE_URL/v1/mission/stop" -Method Post -Headers @{ "x-api-key" = $AUTH_TOKEN }
        Write-Host "[*] All active missions aborted and manager reset." -ForegroundColor Green
    } catch {
        Write-Host "[!] Error: Failed to reset missions. $($_.Exception.Message)" -ForegroundColor Red
    }
    exit 0
}

if ($UpdateSettings) {
    $parts = $UpdateSettings -split ':', 2
    if ($parts.Count -eq 2) {
        $key = $parts[0].Trim()
        $val = $parts[1].Trim()
        # Convert val to boolean if applicable
        if ($val -eq "on" -or $val -eq "true" -or $val -eq "1") { $val = $true }
        elseif ($val -eq "off" -or $val -eq "false" -or $val -eq "0") { $val = $false }

        $payload = @{ $key = $val } | ConvertTo-Json
        try {
            $resp = Invoke-RestMethod -Uri "$BASE_URL/v1/config" -Method Post -Body $payload -ContentType "application/json" -Headers @{ "x-api-key" = $AUTH_TOKEN }
            Write-Host "[*] Settings updated: $($resp.settings | ConvertTo-Json -Compress)" -ForegroundColor Green
        } catch {
            Write-Host "[!] Error: Failed to update settings. $($_.Exception.Message)" -ForegroundColor Red
        }
    } else {
        Write-Host "[!] Error: Invalid settings format. Use key:val (e.g. planning:on)" -ForegroundColor Red
    }
    exit 0
}

if ($ShowStatus) {
    try {
        $status = Invoke-RestMethod -Uri "$BASE_URL/v1/mission/status" -Method Get -Headers @{ "x-api-key" = $AUTH_TOKEN }
        Write-Host "`n--- ANTIGRAVITY MISSION STATUS ---" -ForegroundColor Cyan
        Write-Host "Active Sessions : $($status.active_count)"
        Write-Host "Total Tools Run : $($status.tool_count)"
        Write-Host "Total Tokens    : $($status.total_tokens)"
        $costStr = $status.total_cost.ToString("F4")
        Write-Host "Estimated Cost  : `$ $costStr"
        
        if ($status.active_sessions.Count -gt 0) {
            Write-Host "`nActive Sessions Detail:" -ForegroundColor Gray
            foreach ($rid in $status.active_sessions.psobject.Properties.Name) {
                $s = $status.active_sessions.$rid
                Write-Host "- [$($rid)] $($s.model) ($($s.duration)) - Tokens: $($s.tokens) - Tools: $($s.tools -join ', ')"
            }
        }

        Write-Host "`nRecent Changes:" -ForegroundColor Gray
        foreach ($change in $status.recent_changes) {
            Write-Host "- [$($change.time)] $($change.file) ($($change.type))"
        }
        Write-Host "----------------------------------`n"
    } catch {
        Write-Host "[!] Error: Failed to fetch status. $($_.Exception.Message)" -ForegroundColor Red
    }
    exit 0
}

# 4. Model/Agent Selection
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
    $shouldPick = $Selection
    if (-not $shouldPick -and $ClaudeArgs.Count -eq 0 -and [string]::IsNullOrWhiteSpace($NIM_KEY)) {
        $shouldPick = $true
    }

    if ($shouldPick) {
        Write-Host "[?] Preparing selection..." -ForegroundColor Gray
        $options = @()
        if (Test-Path $MODELS_FILE) {
            $modelsData = Get-Content $MODELS_FILE | ConvertFrom-Json
            foreach ($m in $modelsData.data) {
                $options += [PSCustomObject]@{ Type = "Model"; Name = "nvidia_nim/$($m.id)"; Description = "NVIDIA NIM / Provider Model" }
            }
        }
        if (Test-Path $AGENTS_FILE) {
            $agentsData = Get-Content $AGENTS_FILE | ConvertFrom-Json
            foreach ($agentId in $agentsData.psobject.Properties.Name) {
                $latest = $agentsData.$agentId[-1]
                $options += [PSCustomObject]@{ Type = "Agent"; Name = $agentId; Description = "Managed Agent: $($latest.name)" }
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
    Write-Host "[>] Launching Claude with ${selectionType}: $selectionName..." -ForegroundColor Cyan
} else {
    $env:ANTHROPIC_AUTH_TOKEN = $AUTH_TOKEN
    Write-Host "[>] Launching Claude..." -ForegroundColor Cyan
}

# 5. Execute
if ($ClaudeArgs) {
    claude @ClaudeArgs
} else {
    claude
}
