#Requires -Version 5.1
<#
.SYNOPSIS
  Launch the Volt CLI pipe host in CODESYS for live smoke of the C# toolchain, THE WAY A USER DOES: a normal
  GUI IDE running the shipped `start_volt_codesys.py`, serving `volt.bridge.codesys.<pid>`.

  There was a second, HEADLESS mode (`--noUI` + `run_pipe_headless.py`), and it was the default. It was faster
  to launch and it pumped the message loop itself, because headless CODESYS has none - which meant the whole
  e2e tier exercised a path no engineer takes: a different DLL load and a pump that ships with nothing. It is
  deleted. The IDE is also then USABLE while it serves, which the pumping harness never allowed.

.PARAMETER Action   up (launch, default) | down (stop + kill CODESYS) | logs
.PARAMETER Version  18 or 21 (default 21)
.PARAMETER Project  fixture .project to open
.PARAMETER Wait     (up) block until the pipe is serving and print its NAME, so a caller can drive it without
                    hunting for the pid. Use `-Action pipe` on its own to print the name of an IDE already up.
.PARAMETER Instance name suffix so MULTIPLE CODESYS can run at once (per-instance stop-flag/pid/logs). Each
                    process serves its own volt.bridge.codesys.<pid> pipe (no VOLT_PIPE set), so two instances never
                    collide — this is how the multi-instance path is smoke-tested end to end.
#>
param(
    [ValidateSet("up", "down", "logs", "pipe")]
    [string]$Action = "up",
    [ValidateSet("18", "21")]
    [string]$Version = "21",
    [string]$Project = "$PSScriptRoot\..\test\fixtures\CodesysTestProject.project",
    [string]$Instance = "",
    # -NoBuild skips the pre-launch bridge rebuild (fast re-launch when you KNOW the DLL is current).
    [switch]$NoBuild,
    # -Wait blocks until the pipe answers and prints its name. Without it `up` returns as soon as CODESYS is
    # LAUNCHED, which is minutes before it SERVES — and every caller then reinvents the same polling loop.
    [switch]$Wait
)
$ErrorActionPreference = "Stop"

$dll      = Join-Path $PSScriptRoot "..\src\Volt.Ide.Codesys\bin\Release\net48\Volt.Ide.Codesys.dll"
$scriptPy = Join-Path $PSScriptRoot "run_pipe_production.py"
$install  = if ($Version -eq "21") { "C:\Program Files\CODESYS 3.5.21.40" } else { "C:\Program Files\CODESYS 3.5.18.30" }
$exe      = Join-Path $install "CODESYS\Common\CODESYS.exe"

$work     = Join-Path $env:LOCALAPPDATA "volt-bridge"
if (-not (Test-Path $work)) { New-Item -ItemType Directory -Force $work | Out-Null }
$sfx      = if ($Instance) { "-$Instance" } else { "" }   # per-instance file suffix so two can run concurrently
$stopFlag = Join-Path $work "stop$sfx.flag"
$pidFile  = Join-Path $work "codesys-pipe$sfx.pid"
if (-not (Test-Path $work)) { New-Item -ItemType Directory -Force $work | Out-Null }

function Get-Profile {
    $dir = Join-Path $install "CODESYS\Profiles"
    $p = Get-ChildItem -Path $dir -Filter "*.profile.xml" -File -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $p) { throw "No profile found in $dir" }
    return ($p.Name -replace '\.profile\.xml$', '')
}

# THE live bridge pipe's NAME, or $null. Three traps live in these four lines and each one cost real time:
#   - Git Bash cannot enumerate the pipe namespace at all (`ls //./pipe/` returns empty, SILENTLY), so a caller
#     in bash must ask PowerShell rather than looking itself;
#   - the path cannot be passed in from a shell without the backslashes being eaten on the way;
#   - `Split-Path -Leaf` returns NOTHING for entries under it, because it reads '\.\pipe' as a UNC root.
# All three look identical from outside - a pipe that never appears, i.e. an IDE that seems slow to start.
function Get-BridgePipe {
    [System.IO.Directory]::GetFiles('\\.\pipe\') |
        Where-Object { $_ -like '*volt.bridge.codesys.*' } |
        ForEach-Object { $_.Substring($_.LastIndexOf('\') + 1) } |
        Select-Object -First 1
}

switch ($Action) {
    "down" {
        New-Item -ItemType File -Force $stopFlag | Out-Null
        Start-Sleep -Seconds 2
        if (Test-Path $pidFile) {
            $procId = Get-Content $pidFile
            try { Stop-Process -Id $procId -Force -ErrorAction Stop; Write-Host "killed CODESYS pid $procId" } catch {}
            Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
        }
        Remove-Item $stopFlag -Force -ErrorAction SilentlyContinue
    }
    "pipe" {
        $p = Get-BridgePipe
        if ($p) { $p } else { Write-Error "no volt.bridge.codesys.* pipe - is an IDE up?" }
    }
    "logs" {
        Get-Content (Join-Path $work "bridge-launcher.log") -Tail 40 -ErrorAction SilentlyContinue
    }
    "up" {
        if (-not (Test-Path $exe))     { throw "CODESYS.exe not found: $exe" }
        if (-not (Test-Path $Project)) { throw "Fixture project not found: $Project" }

        # Rebuild the bridge DLL FIRST so the host never loads a STALE build (a stale Release DLL silently
        # serves the OLD wire shape — the "stale bridge" trap; re-record/verify against a freshly-built bridge). Safe
        # here: CODESYS isn't running yet on `up`, so the DLL isn't locked. Skip with -NoBuild for a fast re-launch.
        if (-not $NoBuild) {
            Write-Host "building Volt.Ide.Codesys (Release) so the bridge isn't stale..."
            $proj = Join-Path $PSScriptRoot "..\src\Volt.Ide.Codesys\Volt.Ide.Codesys.csproj"
            & "C:\Program Files\dotnet\dotnet.exe" build $proj -c Release --nologo -v quiet
            if ($LASTEXITCODE -ne 0) { throw "bridge build failed (exit $LASTEXITCODE) - fix it before launching a stale DLL" }
        }
        if (-not (Test-Path $dll))     { throw "Pipe DLL missing (build Volt.Ide.Codesys): $dll" }
        Remove-Item $stopFlag -Force -ErrorAction SilentlyContinue

        $env:VOLT_BRIDGE_DLL      = (Resolve-Path $dll).Path
        $env:VOLT_FIXTURE_PROJECT = (Resolve-Path $Project).Path
        $env:VOLT_STOP_FLAG       = $stopFlag

        $profileName = Get-Profile
        # No --noUI: the production host does not pump a message loop, so without the IDE's own loop nothing
        # serves the pipe.
        $argline = '--profile="{0}" --runscript="{1}"' -f $profileName, (Resolve-Path $scriptPy).Path
        Write-Host "Profile: $profileName"
        Write-Host "DLL:     $($env:VOLT_BRIDGE_DLL)"
        Write-Host "Project: $($env:VOLT_FIXTURE_PROJECT)"
        # NO stdout/stderr redirect: CODESYS's UI process wants its own console handles and redirecting them can
        # wedge startup. That is why the host script writes its own file log - see `logs` below.
        $proc = Start-Process -FilePath $exe -ArgumentList $argline -PassThru -WindowStyle Normal
        $proc.Id | Out-File $pidFile
        Write-Host "CODESYS launched (pid $($proc.Id)). Pipe: volt.bridge.codesys.$($proc.Id)"
        Write-Host "Tail launcher log with: codesys-pipe.ps1 logs"

        if ($Wait) {
            # Opening a real project takes MINUTES; the pipe is the only honest "ready" signal.
            for ($i = 0; $i -lt 120; $i++) {
                $p = Get-BridgePipe
                if ($p) { $p; return }
                Start-Sleep -Seconds 5
            }
            throw "CODESYS launched but no pipe after 10 minutes - see: codesys-pipe.ps1 logs"
        }
    }
}
