## Why

> **CORRECTED 2026-09-08, before any fix was written.** The original framing below — "the push reports success"
> — was WRONG, and the correction is the finding. `volt push` REFUSES this body, correctly and by name. What it
> does not do is roll back the item it had already created, so the project keeps an empty shell wearing the
> engineer's POU name. A later pull materializes that shell, and it reads as five separate losses. There was
> never a silent success; there was a refusal whose wreckage looked like one, and diagnosing it as data loss
> cost the first hour. See `## What was actually wrong` below.

**A graphical POU pushed into an empty TwinCAT project can arrive gutted, and the push reports success.**

Found by the migration finder on its first unblocked TwinCAT run, then ISOLATED to a single file so no other
item and no refusal-recovery is involved (`corpus-migration.ts` over a one-file corpus):

```
pushed                              pulled back
──────                              ───────────
PROGRAM ladderLabel                 PROGRAM ladderLabel
VAR                                 VAR
	coil: BOOL;                      END_VAR
END_VAR
                                    NETWORK 0 FBD
NETWORK 0 LD LABEL: testLabel       END_NETWORK
  coil := ;
END_NETWORK
NETWORK 1 LD LABEL: testLabe2
END_NETWORK
```

Five losses in one push: the DECLARATION, the LANGUAGE (LD → FBD), both network LABELS, the coil, and network 1
entirely. `volt push` printed `pushed 1 item(s)`.

**The lowering is where most of it goes, and that half is measurable offline.** Driving
`TcPlcOpenWriter.WriteProject` over the parsed model directly (model: `LANG=Ld`, 2 networks, labels on both):

- `<interface />` is emitted EMPTY — the declaration never reaches the document.
- the body element is `<FBD>` for an LD model.
- only ONE network is emitted; the label-only network 1 is absent, which is consistent with D25 (PLCopen has
  no network element, so an empty network cannot be stated).
- neither label appears anywhere in the document.

**And the guard that exists for exactly this did not fire.** `Stamp` swallows the importer's
`NotSupportedException` only `when (!CarriesDetail(model) && !LostNetworks(built, model))`, and this model
carries detail — both networks have labels — so the refusal should have propagated and failed the push.
`TcNetworkWriter.Apply` does refuse on a network-count mismatch. Why the refusal did not reach the caller is
UNDIAGNOSED and is the first task: a guard that is right in its reasoning and silent in practice is worse than
no guard, because the comment above it reads as proof.

Scope: the CREATE path only. An existing body is edited in place, where every id and unmodelled member
survives, and the corpora exercise that continuously.

## What was actually wrong

Measured by pushing the same shape three ways:

| pushed | result |
|---|---|
| on its own, into Project14 | **refused** — "the number of networks changes (1 -> 2)" |
| on its own, into Project13 | **refused**, identically |
| after emptying the project | **refused**, identically |
| by the migration, with 8 other items | "accepted", body gutted |

Neither the project nor the emptying was the difference. The refusal fires every time — and every time it
LEAVES THE CREATED ITEM BEHIND:

```
PROGRAM VltProbeLadder
VAR
END_VAR

NETWORK 0 FBD
END_NETWORK
```

That shell is what the migration's recovery pull picked up and the comparison read as drift. `PushService`
creates the item, then writes its content; the create site already says *"a refused push must not leave an
orphaned, unlisted stub POU behind"* and validates the pushed TEXT first — but TwinCAT's graphical create
resolves the body through a PLCopen import, and the network-count refusal is only knowable AFTER the item
exists.

**The fix is the rollback the create site already promised**, not a change to the lowering: a content write
that fails deletes the item this op created, from an exception FILTER so the vendor's own reason keeps its
stack and is what reaches the engineer. Best-effort, and it logs loudly if the shell survives — replacing a
real refusal with a rollback failure would be the worse outcome.

## What Changes

- **Diagnose why the refusal is swallowed**, before changing any lowering. The bug may be one missing throw.
- **A push that cannot create the body it was given must FAIL**, not land a partial one. That is this repo's
  standing rule for the create path — it is why `ResolveGraphicalBody` already refuses an empty import — and
  the rule is what makes a migration trustworthy at all.
- **Then, separately, decide what the lowering should carry.** The declaration and the view mode look
  addressable; an empty network is forced by PLCopen (D25) and belongs in a named refusal rather than a fix.
- Every part gets an OFFLINE test in `volt-cli` that fails without it. The lowering half needs no live IDE.

## Impact

- `packages/volt-cli/src/Volt.Ide.Twincat/Driver/BeckhoffDriver.Content.cs` (`Stamp`, `ResolveBody`, `WriteOne`)
- `packages/volt-cli/src/Volt.Ide.Twincat/Ide/TcPlcOpenWriter.cs` (the lowering)
- `packages/volt-cli/src/Volt.Ide.Twincat/Ide/TcNetworkWriter.cs` (`Apply`'s refusal path)
- `packages/volt-cli/test/Volt.Ide.Twincat.Tests/` — the offline half
