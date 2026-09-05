# Probe: where a TwinCAT task's schedule really lives, and whether it can be written.
#
# The PLC task item (TREEITEMTYPE_PLCTASK, 621) carries only `<LinkedTask>TIRT^<name></LinkedTask>` - the
# schedule sits on the SYSTEM task it points at, and the ordered POU calls are its own child items
# (TREEITEMTYPE_PLCPROGREF, 650), named by POU. This drives both halves against a live XAE.
#
# Read-only by default. `-Write` changes the priority/cycle time of the task and puts them back, which is the
# only way to answer whether ConsumeXml on a system task takes. Run it against a FIXTURE project, never an
# engineer's own - `test/fixtures/TwinCAT Project14` is what it was measured on.
param([switch]$Write)

$ErrorActionPreference = "Stop"

function Get-XaeDte {
    foreach ($p in @("TcXaeShell.DTE.15.0", "TcXaeShell.DTE", "VisualStudio.DTE.15.0")) {
        try { return [Runtime.InteropServices.Marshal]::GetActiveObject($p) } catch {}
    }
    throw "no running XAE - open the fixture solution in TcXaeShell first"
}

$dte = Get-XaeDte
$sm = $dte.Solution.Projects.Item(1).Object
Write-Host "solution: $($dte.Solution.FullName)`n"

# The PLC project's own tree hangs off the system-manager node as NestedProject (the driver's PlcRoot()).
$plcNode = $sm.LookupTreeItem("TIPC").Child(1)
$root = $plcNode.NestedProject
$task = $null
for ($i = 1; $i -le $root.ChildCount; $i++) {
    $c = $root.Child($i)
    if ($c.ItemType -eq 621) { $task = $c; break }
}
if (-not $task) { throw "no PLC task (item type 621) under $($root.Name)" }

$linked = ([xml]$task.ProduceXml()).TreeItem.PlcTaskDef.LinkedTask
Write-Host "plc task : $($task.Name)  -> linked=$linked"
$calls = @()
for ($i = 1; $i -le $task.ChildCount; $i++) {
    $c = $task.Child($i)
    if ($c.ItemType -eq 650) { $calls += $c.Name }
}
Write-Host "calls    : $($calls -join ', ')"

function Get-Sched {
    $d = ([xml]$sm.LookupTreeItem($linked).ProduceXml()).TreeItem.TaskDef
    return [pscustomobject]@{ Priority = $d.Priority; CycleTime = $d.CycleTime }
}
$before = Get-Sched
Write-Host "schedule : Priority=$($before.Priority)  CycleTime=$($before.CycleTime) (100ns ticks)"

if (-not $Write) { Write-Host "`n(read-only; pass -Write to test whether the two writes take)"; return }

# --- 1. the schedule, onto the SYSTEM task -----------------------------------------------------------------
# Re-lookup after every mutation: a TwinCAT tree item is invalidated by one.
$want = [int]$before.Priority + 1
Write-Host "`n[schedule] writing Priority=$want ..."
$sm.LookupTreeItem($linked).ConsumeXml("<TreeItem><TaskDef><Priority>$want</Priority></TaskDef></TreeItem>")
$after = Get-Sched
Write-Host "[schedule] read back Priority=$($after.Priority)  CycleTime=$($after.CycleTime)"
Write-Host $(if ($after.Priority -eq "$want") { "[schedule] TOOK" } else { "[schedule] IGNORED - ConsumeXml is not the write path" })
$sm.LookupTreeItem($linked).ConsumeXml("<TreeItem><TaskDef><Priority>$($before.Priority)</Priority></TaskDef></TreeItem>")
Write-Host "[schedule] restored Priority=$((Get-Sched).Priority)"

# --- 2. the call list, as children of the PLC TASK ---------------------------------------------------------
# A POU the task does not already call, so the probe adds rather than replaces and can put it back by deleting.
$spare = $null
for ($i = 1; $i -le $root.ChildCount; $i++) {
    $c = $root.Child($i)
    if ($c.ItemType -eq 602 -and $calls -notcontains $c.Name) { $spare = $c.Name; break }
}
if (-not $spare) { Write-Host "`n[calls] no spare POU at the project root to add - skipped"; return }

Write-Host "`n[calls] adding a call to '$spare' (TREEITEMTYPE_PLCPROGREF, 650) ..."
try {
    $sm.LookupTreeItem("$($task.PathName)").CreateChild($spare, 650, "", [Type]::Missing)
    $t2 = $sm.LookupTreeItem("$($task.PathName)")
    $now = @(); for ($i = 1; $i -le $t2.ChildCount; $i++) { if ($t2.Child($i).ItemType -eq 650) { $now += $t2.Child($i).Name } }
    Write-Host "[calls] read back: $($now -join ', ')"
    Write-Host $(if ($now -contains $spare) { "[calls] TOOK" } else { "[calls] IGNORED - CreateChild is not the write path" })
    if ($now -contains $spare) {
        $sm.LookupTreeItem("$($task.PathName)").DeleteChild($spare)
        $t3 = $sm.LookupTreeItem("$($task.PathName)")
        $end = @(); for ($i = 1; $i -le $t3.ChildCount; $i++) { if ($t3.Child($i).ItemType -eq 650) { $end += $t3.Child($i).Name } }
        Write-Host "[calls] restored: $($end -join ', ')"
    }
} catch { Write-Host "[calls] FAILED: $($_.Exception.Message)" }
