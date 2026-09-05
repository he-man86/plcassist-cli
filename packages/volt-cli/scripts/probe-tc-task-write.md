# Probe: can a TwinCAT task be WRITTEN? (needs a machine with TwinCAT XAE)

`.task` is writable on CODESYS and read-only on TwinCAT. That asymmetry is declared and gated
(`test/Volt.Repo.Gates/VendorCapabilityParityTests.cs`), and it exists for ONE unanswered question, not because
the write looks hard. This is that question, and the run that settles it.

## What is already known (no hardware needed)

* TwinCAT keeps a PLC task's schedule **in the PLC project**, in the `.TcTTO` beside the POUs — committed
  fixture `test/fixtures/TwinCAT Project13/TwinCAT Project13/Untitled1/PlcTask.TcTTO`:

  ```xml
  <Task Name="PlcTask" Id="{…}">
    <!--CycleTime in micro seconds.-->
    <CycleTime>10000</CycleTime>
    <Priority>20</Priority>
    <PouCall><Name>PLC_PRG</Name></PouCall>
  </Task>
  ```

* The **same task is written again** in the system configuration (`TwinCAT Project13.tsproj`) as
  `<Task Id="3" Priority="20" CycleTime="100000">` — 100ns ticks, not µs. Both say 10 ms. Two copies, two units.
* The driver already has the write mechanism: `TcItemArchive.RoundTrip` exports an item, hands the archive to a
  `rewrite` callback and re-imports it — `SetMemberBodies` uses exactly that to rewrite XML inside a `.TcPOU`.

So the machinery exists and the data is reachable. What is NOT known is whether writing it means anything.

## The question

**Which copy does the runtime honour — the PLC document, or the system tree?**

If the system tree is authoritative, rewriting the `.TcTTO` produces a file that looks right in git, reads back
correctly through Volt, and changes nothing about what the PLC actually runs. That is the exact failure this
project has already been bitten by twice: CODESYS's task call list accepts `remove()` and silently ignores it
(DIALECT C19), and `???` on a box output pin looked like a diagnosable error for months (C18). A write that
reports success and schedules nothing is worse than no write at all.

Two smaller unknowns ride along:

* does `ExportChild` accept a **task** node? It refuses POU MEMBERS outright — *"The tree item 'Deep' cannot be
  exported seperately because it has no document file"* — so the same refusal is plausible here.
* does `ImportChild` preserve the task's link to its system task, or re-create an unlinked one?

## The run

On a machine with XAE, against **a copy** of a project (never an original):

1. Bring the bridge up on the copy and confirm `volt status` is clean.
2. Note the task's current cycle time in the XAE task editor.
3. Export the task node through `TcItemArchive`-style export. **If it refuses, stop — that is the answer**, and
   the write needs a different route (the system tree, or the automation interface's task object).
4. Rewrite `<Priority>` and `<CycleTime>` in the archive, re-import.
5. Then the three things that matter, in order:
   * does the **XAE task editor** show the new values?
   * does the **`.tsproj` system entry** show them (converted: µs × 10 = 100ns ticks)?
   * **activate the configuration** and confirm the runtime cycle actually changed.

Answer (5) and the gap either closes or gets a documented reason it cannot. Either way, update
`VendorCapabilityParityTests.Writable["task"]` — the gate will fail until it is, which is deliberate.

## If it works

The engine side is already vendor-neutral and needs nothing: `TaskDescriptorFormat` is shared, `PushService`
routes by kind, and `ICodeStore.WriteTask` takes typed settings. TwinCAT needs the `.TcTTO` reader (translating
`CycleTime`/µs and `PouCall` into `TaskSettings`) plus the archive rewrite — and the parity row flips to
`Twincat: true`.

A reader was written and then **reverted** on 2026-09-05 rather than shipped unverified; the shape it had is in
this file's history if it is useful, but re-deriving it from the fixture above is a short job.
