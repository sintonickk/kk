param(
    [string]$ProcessName = "",
    [string]$CommandMatch = "",
    [Parameter(Mandatory=$true)]
    [string]$StartScript,
    [int]$CheckInterval = 10,
    [string]$WorkingDir = "",
    [string]$LogPath = ""
)

# Simple logger
function Write-Log {
    param([string]$Message)
    $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $line = "[$ts] $Message"
    Write-Host $line
    if ($LogPath -and (Test-Path (Split-Path -Path $LogPath -Parent) -ErrorAction SilentlyContinue)) {
        try { Add-Content -Path $LogPath -Value $line -Encoding UTF8 } catch {}
    }
}

# Resolve StartScript and default WorkingDir
$StartScript = [System.IO.Path]::GetFullPath($StartScript)
if (-not $WorkingDir -or $WorkingDir.Trim() -eq "") {
    $WorkingDir = Split-Path -Path $StartScript -Parent
}

if ($LogPath -and -not (Test-Path (Split-Path -Path $LogPath -Parent))) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Path $LogPath -Parent) | Out-Null
}

if (-not (Test-Path $StartScript)) {
    Write-Log "StartScript not found: $StartScript"
    exit 1
}

if ([string]::IsNullOrWhiteSpace($ProcessName) -and [string]::IsNullOrWhiteSpace($CommandMatch)) {
    Write-Log "Either -ProcessName or -CommandMatch must be provided."
    exit 1
}

function Test-TargetProcess {
    try {
        if ($ProcessName -and $ProcessName.Trim() -ne "") {
            $procs = Get-Process -Name $ProcessName -ErrorAction SilentlyContinue
            if ($procs) { return $true }
        }
        if ($CommandMatch -and $CommandMatch.Trim() -ne "") {
            $list = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match $CommandMatch }
            if ($list) { return $true }
        }
    } catch {}
    return $false
}

function Start-Target {
    $ext = [System.IO.Path]::GetExtension($StartScript).ToLowerInvariant()
    try {
        switch ($ext) {
            ".ps1" {
                Start-Process -FilePath "powershell" -ArgumentList @("-NoProfile","-ExecutionPolicy","Bypass","-File","`"$StartScript`"") -WorkingDirectory $WorkingDir | Out-Null
            }
            ".bat" { Start-Process -FilePath $StartScript -WorkingDirectory $WorkingDir | Out-Null }
            ".cmd" { Start-Process -FilePath $StartScript -WorkingDirectory $WorkingDir | Out-Null }
            ".exe" { Start-Process -FilePath $StartScript -WorkingDirectory $WorkingDir | Out-Null }
            ".py"  { Start-Process -FilePath "python" -ArgumentList @("`"$StartScript`"") -WorkingDirectory $WorkingDir | Out-Null }
            default { Start-Process -FilePath $StartScript -WorkingDirectory $WorkingDir | Out-Null }
        }
        Write-Log "Started: $StartScript"
    } catch {
        Write-Log "Failed to start: $StartScript. Error: $($_.Exception.Message)"
    }
}

Write-Log "Watchdog started. ProcessName='$ProcessName' CommandMatch='$CommandMatch' Interval=${CheckInterval}s StartScript='$StartScript'"

try {
    while ($true) {
        $running = Test-TargetProcess
        if (-not $running) {
            Write-Log "Target process not running. Attempting to start..."
            Start-Target
            Start-Sleep -Seconds 3
        }
        Start-Sleep -Seconds $CheckInterval
    }
} catch [System.Exception] {
    Write-Log "Watchdog loop error: $($_.Exception.Message)"
    exit 1
}
