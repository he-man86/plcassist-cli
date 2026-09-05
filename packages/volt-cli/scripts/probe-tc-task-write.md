# TwinCAT tasks: where the schedule really lives (and what a write would have to touch)

`.task` is writable on CODESYS and read-only on TwinCAT. That asymmetry is declared and gated
(`test/Volt.Repo.Gates/VendorCapabilityParityTests.cs`). This is what is known about closing it.

## Measured on a live TwinCAT (2026-09-05, TcXaeShell 15.0, `TwinCAT Project14`, read-only)

Volt materializes that project's only task as:

```
PlcTask.task    folder="PlcTask"
    Name=PlcTask
    linked-task=TIRT^PlcTask
```

Three things follow, and together they redirect the obvious implementation:

1. **`TIRT^PlcTask` is a SYSTEM-MANAGER PATH.** `TIRT` is the real-time/task tree — the same kind of path the
   driver already resolves for the I/O tree (`_om.LookupTreeItem("TIID")`, `BeckhoffDriver.Tree.cs`). So the
   PLC-side task really is a *reference*, and the schedule it points at is a system object.
2. **The PLC project's `.TcTTO` is not what the bridge reads.** `ProduceXml` on the task node returns item
   METADATA (the two lines above), not the task document. The `.TcTTO` on disk does carry `<CycleTime>` /
   `<Priority>` / `<PouCall>` (committed fixture `TwinCAT Project13/…/Untitled1/PlcTask.TcTTO`), but it is the
   PLC-side copy, and the system tree holds the same task again with a *different unit* — `CycleTime="100000"`
   in 100ns ticks against the document's `10000` µs.
3. **The call list is not on the wire as children.** `task_call_reference` (PLCPROGREF, 650) items: none. The
   system task carries its POUs as `<TaskPouOid Prio="20" OTCID="#x08502001"/>` — by OBJECT ID, not by name.

## What that means for a shared `.task`

A reader written against the `.TcTTO` would read the wrong copy. One was written on 2026-09-05 and **reverted
before shipping** for exactly the reason this file now documents: it looked right, parsed the committed fixture
correctly, and would have described a schedule the runtime may not use.

The route that matches the vendor's own model is: follow `linked-task` → `LookupTreeItem("TIRT^<name>")` →
read that system object. The driver already has `_sysManager` and does this for `TIID`, so the mechanism exists;
what does not exist is any measurement of what the system task's XML looks like, or of whether writing it takes.

Rendering a `Calls:` line of POU NAMES additionally needs OTCID → name resolution, which CODESYS does not need
because it keeps the call list as names on the task itself. That is a real asymmetry, not a formatting one.

## The run that would settle a WRITE

On a machine with XAE, against **a copy** of a project — never an original:

1. Read `TIRT^<task>` and record its XML. That alone answers "can we even see the schedule?" and is read-only.
2. Change `Priority` there, and check the XAE task editor reflects it.
3. **Activate the configuration** and confirm the runtime cycle actually changed — the only proof that the copy
   written is the copy that runs.
4. Separately: does writing the PLC-side `.TcTTO` change the system entry, or is it ignored? If ignored, that
   settles that the `.TcTTO` route is a dead end for writes as well as reads.

If the system tree turns out to be authoritative and writable, the engine side needs nothing new:
`TaskDescriptorFormat` is shared, `PushService` routes by kind, and `ICodeStore.WriteTask` already takes typed
settings. TwinCAT needs the system-task reader/writer, and
`VendorCapabilityParityTests.Writable["task"]` flips to `Twincat: true` — the gate fails until it does, which is
deliberate.

## Why the caution

A write that reports success and schedules nothing is worse than no write. This project has been bitten twice by
exactly that: CODESYS's task call list accepts `remove()` and silently ignores it (DIALECT C19), and `???` on a
box output pin read as a diagnosable error for months (C18). Both were found by measuring, not by reasoning.
