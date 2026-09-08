#Requires -Version 5.1
<#
.SYNOPSIS
  Open the committed TwinCAT fixture solutions in TcXaeShell - the TwinCAT analogue of codesys-pipe.ps1, for the
  live multi-XAE e2e. Unlike CODESYS, TwinCAT has NO in-proc pipe host: the connector's VoltBridgeTwincat worker
  attaches to whatever XAE windows are running over the COM ROT. So this script only OPENS the IDEs; the worker
  (already supervised by the connector) discovers them. TcXaeShell is Visual-Studio-based and has no headless mode,
  so this is a LOCAL live-bridge tier - deterministic (committed fixtures) but not CI.

.PARAMETER Action  up (open, default) | down (close the ones this script opened)
.PARAMETER Which   both (default) | 13 | 14 - which fixture(s) to open. 'both' is the multi-XAE scenario.
.PARAMETER Solution a .sln OUTSIDE the fixtures to open instead - a scratch copy for a migration target, say.
                    Committed fixtures are the deterministic default; this is for a throwaway that must start
                    from a known state every run, which a fixture cannot be if a migration empties it.
#>
param(
    [ValidateSet("up", "down")] [string]$Action = "up",
    [ValidateSet("both", "13", "14")] [string]$Which = "both",
    [string]$Solution = ""
)
$ErrorActionPreference = "Stop"

$ide  = "C:\Program Files (x86)\Beckhoff\TcXaeShell\Common7\IDE\TcXaeShell.exe"
$test = Join-Path $PSScriptRoot "..\test\fixtures"
$slns = [ordered]@{
    "13" = Join-Path $test "TwinCAT Project13\TwinCAT Project13.sln"
    "14" = Join-Path $test "TwinCAT Project14\TwinCAT Project14.sln"
}
$pick = if ($Which -eq "both") { @("13", "14") } else { @($Which) }

$work    = Join-Path $env:LOCALAPPDATA "volt-bridge"
if (-not (Test-Path $work)) { New-Item -ItemType Directory -Force $work | Out-Null }
$pidFile = Join-Path $work "twincat-instances.pids"

# The tracked pids, as INTS, skipping anything that is not one. A corrupt entry must not stop the rest from
# being closed - the file is written by a previous run and read by this one, so it is the least trustworthy
# input the script has.
function Read-Pids([string]$path) {
    if (-not (Test-Path $path)) { return @() }
    @(Get-Content $path | ForEach-Object { $_.Trim() } | Where-Object { $_ -match '^\d+$' } | ForEach-Object { [int]$_ })
}

switch ($Action) {
    "down" {
        if (Test-Path $pidFile) {
            foreach ($procId in (Read-Pids $pidFile)) {
                try { Stop-Process -Id $procId -Force -ErrorAction Stop; Write-Host "closed TcXaeShell pid $procId" } catch {}
            }
            Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
        } else { Write-Host "no tracked TcXaeShell instances to close" }
    }
    "up" {
        if (-not (Test-Path $ide)) { throw "TcXaeShell.exe not found: $ide" }
        $pids = @()
        # An explicit -Solution replaces the fixture picks entirely: a caller that names a solution wants THAT
        # one open and nothing else, and silently adding the fixtures beside it would give the connector two
        # XAE windows to choose between.
        $open = if ($Solution) { [ordered]@{ "scratch" = $Solution } }
                else { $picked = [ordered]@{}; foreach ($k in $pick) { $picked[$k] = $slns[$k] }; $picked }
        foreach ($k in $open.Keys) {
            $sln = $open[$k]
            if (-not (Test-Path $sln)) { throw "solution missing: $sln" }
            $p = Start-Process -FilePath $ide -ArgumentList ('"{0}"' -f (Resolve-Path $sln).Path) -PassThru
            $pids += $p.Id
            Write-Host "opened $(if ($Solution) { Split-Path $sln -Leaf } else { "TwinCAT Project$k" }) (TcXaeShell pid $($p.Id))"
        }
        # MERGE with the instances already tracked, never overwrite. `up -Which 13` then `up -Which 14` used to
        # replace the file, so `down` closed only the second and left the first running — an orphan XAE holding the
        # fixture open, which is precisely the state the teardown rule exists to avoid. Dead pids are dropped on the
        # way through so the file cannot grow stale entries.
        $live = @()
        if (Test-Path $pidFile) {
            $live = @(Read-Pids $pidFile | Where-Object { (Get-Process -Id $_ -ErrorAction SilentlyContinue) -ne $null })
        }
        # `@(...)` on BOTH sides. `$live + $pids` did STRING concatenation whenever the file held exactly ONE
        # pid, because Get-Content returns a scalar for a one-line file: "22620" + 10388 wrote "2262010388", a
        # number too large for Int32. `down` then failed to kill anything and left every IDE running - which is
        # how ten orphaned TcXaeShell windows accumulated before anyone noticed.
        (@($live) + @($pids) | Select-Object -Unique) | Out-File $pidFile -Encoding ascii
        Write-Host ""
        Write-Host "TcXaeShell is loading; give it ~30-60s to open the PLC project(s). The connector worker then"
        Write-Host "attaches over the COM ROT. Run the multi-XAE e2e from packages/volt-cli:"
        Write-Host '  $env:VOLT_PIPE="volt.bridge.twincat"; $env:VOLT_VENDOR="twincat"; bun test test/e2e'
    }
}
