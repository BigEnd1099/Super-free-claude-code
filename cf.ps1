# Antigravity Proxy Launcher - Unified Control Interface
# Usage: .\cf.ps1 [flags] [claude args]

$SCRIPT_DIR = $PSScriptRoot
$ENV_FILE = Join-Path $SCRIPT_DIR ".env"
$LOG_FILE = Join-Path $SCRIPT_DIR "server.log"
$AGENTS_FILE = Join-Path $SCRIPT_DIR "agents_db.json"
$MODELS_FILE = Join-Path $SCRIPT_DIR "nvidia_nim_models.json"

# --- 1. Manual Argument Parsing ---
$Selection = $false
$Model = $null
$Agent = $null
$ShowLogs = $false
$ShowStatus = $false
$ResetMissions = $false
$ShowHelp = $false
$UpdateSettings = $null
$BatchMode = $false
$Workspace = $null
$ClaudeArgs = @()

$i = 0
while ($i -lt $args.Count) {
    $arg = $args[$i]
    switch -Regex ($arg) {
        "^-(Pick|Select)$" { $Selection = $true }
        "^-(Model|m)$" { $i++; if ($i -lt $args.Count) { $Model = $args[$i] } }
        "^-(Agent|a)$" { $i++; if ($i -lt $args.Count) { $Agent = $args[$i] } }
        "^-(Logs|l)$" { $ShowLogs = $true }
        "^-(Status|s)$" { $ShowStatus = $true }
        "^-(Reset|r)$" { $ResetMissions = $true }
        "^-(Settings|cfg)$" { $i++; if ($i -lt $args.Count) { $UpdateSettings = $args[$i] } }
        "^-(Batch|b)$" { $BatchMode = $true }
        "^-(Workspace|w)$" { $i++; if ($i -lt $args.Count) { $Workspace = $args[$i] } }
        "^-(Help|h)$" { $ShowHelp = $true }
        default { $ClaudeArgs += $arg }
    }
    $i++
}

# --- 2. Helper Functions ---
function Get-EnvValue($key) {
    if (Test-Path $ENV_FILE) {
        $line = Get-Content $ENV_FILE | Where-Object { $_ -match "^\s*${key}\s*=" } | Select-Object -Last 1
        if ($line) { return ($line -split '=', 2)[1].Trim().Trim('"').Trim("'") }
    }
    return $null
}

function Show-Help {
    Write-Host "`n🛰️  ANTIGRAVITY PROXY - POWER LAUNCHER" -ForegroundColor Cyan
    Write-Host "Usage: cf [options] [claude_args]`n" -ForegroundColor White
    Write-Host "OPTIONS:" -ForegroundColor Gray
    Write-Host "  -Pick, -Select     Interactive GUI to select model or agent."
    Write-Host "  -m, -Model <id>    Directly use a specific provider model."
    Write-Host "  -a, -Agent <id>    Directly use a specific Managed Agent persona."
    Write-Host "  -s, -Status        Fetch real-time mission metrics and uptime."
    Write-Host "  -l, -Logs          Tail the proxy server logs."
    Write-Host "  -r, -Reset         Abort all active proxy sessions."
    Write-Host "  -cfg <key>:<val>   Update dynamic settings (e.g., -cfg planning:on)."
    Write-Host "  -b, -Batch         Headless mode for automation (skips permissions)."
    Write-Host "  -w, -Workspace <p> Override the synchronized project root."
    Write-Host "  -h, -Help          Show this help menu.`n"
    Write-Host "INTELLIGENCE SETTINGS:" -ForegroundColor Gray
    Write-Host "  planning:on/off, adversarial:on/off, thinking:on/off, raw_mode:on/off`n"
}

# --- 3. Configuration ---
$PORT = Get-EnvValue "PORT"; if (-not $PORT) { $PORT = 8082 }
$BASE_URL = "http://localhost:$PORT"
$AUTH_TOKEN = Get-EnvValue "ANTHROPIC_AUTH_TOKEN"; if (-not $AUTH_TOKEN) { $AUTH_TOKEN = "freecc" }

# --- 4. Server Health & Verification ---
function Verify-Environment {
    Write-Host "[*] Verifying Super FCC Bridge..." -ForegroundColor Gray
    try {
        $resp = Invoke-WebRequest -Uri "$BASE_URL/v1/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        Write-Host "[+] Bridge Online." -ForegroundColor Green
    }
    catch {
        Write-Host "[!] Bridge Offline. Attempting auto-start..." -ForegroundColor Yellow
        Start-Process "uv" -ArgumentList "run", "uvicorn", "server:app", "--port", $PORT, "--host", "0.0.0.0" -WindowStyle Minimized -WorkingDirectory $SCRIPT_DIR
        Start-Sleep -Seconds 5
    }
    
    if (Test-Path "$SCRIPT_DIR/task.md") {
        Write-Host "[*] Active task found. Synchronizing context..." -ForegroundColor Cyan
    }
}

# --- 6. Project Context & Synchronization ---
$current_root = if ($Workspace) { Resolve-Path $Workspace } else { $PWD.Path }
$env:GRAPHIFY_ROOT = $current_root

Verify-Environment

Write-Host "[*] Synchronizing project context: $current_root" -ForegroundColor Gray
$retries = 3
while ($retries -gt 0) {
    try {
        Invoke-RestMethod -Uri "$BASE_URL/v1/graph/project" -Method Post -Body (@{ path = $current_root } | ConvertTo-Json) -ContentType "application/json" -Headers @{ "x-api-key" = $AUTH_TOKEN } -ErrorAction Stop
        Write-Host "[+] Context synchronized." -ForegroundColor Green
        break
    } catch {
        $retries--
        if ($retries -gt 0) { Start-Sleep -Seconds 1 }
    }
}

# --- 5. Utility Dispatch (Early Exit) ---
if ($ShowHelp) { Show-Help; exit 0 }

if ($ShowLogs) {
    if (Test-Path $LOG_FILE) {
        Write-Host "[*] Tailing proxy logs (Ctrl+C to stop)..." -ForegroundColor Cyan
        Get-Content $LOG_FILE -Wait -Tail 20
    }
    else { Write-Host "[!] Log file not found." -ForegroundColor Red }
    exit 0
}

if ($ResetMissions) {
    try {
        Invoke-RestMethod -Uri "$BASE_URL/v1/mission/stop" -Method Post -Headers @{ "x-api-key" = $AUTH_TOKEN } -ErrorAction Stop
        Write-Host "[*] All active missions aborted." -ForegroundColor Green
    }
    catch { Write-Host "[!] Super FCC Offline: $($_.Exception.Message)" -ForegroundColor Red }
    exit 0
}

if ($UpdateSettings) {
    $parts = $UpdateSettings -split ':', 2
    if ($parts.Count -eq 2) {
        $val = $parts[1].Trim()
        if ($val -eq "on" -or $val -eq "true") { $val = $true } elseif ($val -eq "off" -or $val -eq "false") { $val = $false }
        $payload = @{ $parts[0].Trim() = $val } | ConvertTo-Json
        try {
            Invoke-RestMethod -Uri "$BASE_URL/v1/config" -Method Post -Body $payload -ContentType "application/json" -Headers @{ "x-api-key" = $AUTH_TOKEN } -ErrorAction Stop
            Write-Host "[*] Settings updated." -ForegroundColor Green
        }
        catch { Write-Host "[!] Super FCC Offline: $($_.Exception.Message)" -ForegroundColor Red }
    }
    else { Write-Host "[!] Invalid format. Use key:val" -ForegroundColor Red }
    exit 0
}

if ($ShowStatus) {
    try {
        $status = Invoke-RestMethod -Uri "$BASE_URL/v1/mission/status" -Method Get -Headers @{ "x-api-key" = $AUTH_TOKEN } -ErrorAction Stop
        $config = Invoke-RestMethod -Uri "$BASE_URL/v1/config" -Method Get -Headers @{ "x-api-key" = $AUTH_TOKEN } -ErrorAction Stop
        Write-Host "`n--- ANTIGRAVITY STATUS ---" -ForegroundColor Cyan
        Write-Host "Uptime:    $($status.uptime)"
        Write-Host "Active:    $($status.active_count) sessions"
        Write-Host "Tokens:    $($status.total_tokens)"
        Write-Host "Cost:      $($status.total_cost) USD"
        Write-Host "`n--- ENGINE CONFIG ---" -ForegroundColor Cyan
        Write-Host "Model:     $($config.model)"
        Write-Host "Planning:  $($config.planning)"
        Write-Host "Adversary: $($config.adversarial)"
        Write-Host ""
    }
    catch { Write-Host "[!] Super FCC Offline: $($_.Exception.Message)" -ForegroundColor Red }
    exit 0
}


if ($args -contains "-mcp") {
    Set-Location $SCRIPT_DIR
    #SWrite-Host "[>] Starting Super FCC MCP Server (stdio)..." -ForegroundColor Magenta
    uv run --quiet python api/mcp_server.py
    exit 0
}

<# $serverRunning = $false
try {
    $resp = Invoke-WebRequest -Uri "$BASE_URL/v1/health" -UseBasicParsing -ErrorAction SilentlyContinue
    if ($resp.StatusCode -eq 200) { $serverRunning = $true }
}
catch {}

if (-not $serverRunning) {
    Write-Host "[*] Starting Super FCC Proxy..." -ForegroundColor Cyan
    Start-Process "uv" -ArgumentList "run", "uvicorn", "server:app", "--port", $PORT, "--host", "0.0.0.0" -WindowStyle Minimized
    $retries = 5
    while (-not $serverRunning -and $retries -gt 0) {
        Start-Sleep -Seconds 2
        try {
            $resp = Invoke-WebRequest -Uri "$BASE_URL/v1/health" -UseBasicParsing -ErrorAction SilentlyContinue
            if ($resp.StatusCode -eq 200) { $serverRunning = $true }
        }
        catch {}
        $retries--
    }
    if (-not $serverRunning) { Write-Host "[!] Failed to initialize server circuit breaker." -ForegroundColor Red; exit 1 }
} #>

# --- 6. Model/Agent Selection ---
$target = $null
if ($Model) { $target = $Model }
elseif ($Agent) { $target = $Agent; if (-not $target.StartsWith("agent_")) { $target = "agent_$target" } }
elseif ($Selection) {
    $options = @()
    if (Test-Path $MODELS_FILE) { (Get-Content $MODELS_FILE | ConvertFrom-Json).data | ForEach-Object { $options += [PSCustomObject]@{ Type = "Model"; Name = "nvidia_nim/$($_.id)"; Desc = $_.id } } }
    if (Test-Path $AGENTS_FILE) { 
        $db = Get-Content $AGENTS_FILE | ConvertFrom-Json
        $db.psobject.Properties.Name | ForEach-Object { $options += [PSCustomObject]@{ Type = "Agent"; Name = $_; Desc = $db.$_[-1].name } }
    }
    if ($options.Count -gt 0) {
        $choice = $options | Out-GridView -Title "Antigravity Selection" -OutputMode Single
        if ($choice) { $target = $choice.Name }
    }
}

# --- 7. Environment & Execution ---
$env:ANTHROPIC_BASE_URL = $BASE_URL
$env:ANTHROPIC_AUTH_TOKEN = if ($target) { "${AUTH_TOKEN}:$target" } else { $AUTH_TOKEN }

if ($BatchMode) {
    Write-Host "[>] Launching in BATCH mode..." -ForegroundColor Yellow
    $ClaudeArgs += "--dangerously-skip-permissions"
    $ClaudeArgs += "--output-format"
    $ClaudeArgs += "stream-json"
    $ClaudeArgs += "--verbose"
}

Write-Host "[>] Launching Claude Code..." -ForegroundColor Cyan
# Using --% to stop parsing and passing the args array ensures best quote preservation
if ($ClaudeArgs.Count -gt 0) {
    # Splatting @ClaudeArgs is generally safer than --% for dynamic arrays in modern PS
    claude @ClaudeArgs
}
else {
    <#   
    claude
}
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
        }
        else {
            $env:ANTHROPIC_AUTH_TOKEN = $AUTH_TOKEN
            Write-Host "[>] Launching Claude..." -ForegroundColor Cyan
        }

        # 5. Execute
        if ($ClaudeArgs) {
            claude @ClaudeArgs
        }
        else {
            claude
        }
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
} else { #>
    #    
    claude
}
