## Why

**Four graphical shapes CODESYS creates and TwinCAT refuses.** The e2e suite is one suite run against either
vendor, and "a pass on one and a fail on the other is a real parity bug, not an expected difference" — its own
README says so. Today four tests take a vendor branch, and every branch is a gap to close, not a difference to
respect.

They surfaced together, in one run, and only because tests that had never been pointed at TwinCAT finally were:

| Shape | What TwinCAT does |
|---|---|
| an Execute box (ST inside FBD) | PLCopen has no element for one — refused (the only one of the four that was already known) |
| a box's **embedded output pin** — `t1(… ET => el)` | the importer honours an `outVariable` wired to the pin by lowering it to a **separate assignment**, not an output on the box |
| an **unconnected input pin** — `FB(xEnable := , …)` | lowers to a rung terminator the importer has no form for |
| a wired **EN input** | the importer folds the enable into the box as an ordinary input, changing what the program does (long-standing, deliberate refusal) |
| **network GROUPING** — one pushed network | comes back as one network on CODESYS and as N on TwinCAT, one per connected component (`grouping.test.ts` asserts `[1,1,2,2]` vs `[1,1,1,1]`) |

**Grouping is the odd one out, and it is not a refusal — it is a silent reshape.** The other four are refused,
so an engineer is told. A body pushed as ONE network comes back as several on TwinCAT because the PLCopen
importer groups by connected rung, and nothing warns. It was left out of the original list because it is
measured and stable, not broken — but "the same source gives the same result on both bridges" is the contract,
and this breaks it in the one way the engineer cannot see. It may turn out to be unfixable through the importer,
in which case the answer is a stated refusal like the others rather than a quiet regrouping.

**Treat the whole list as provisional, because the two vendors have not had equal scrutiny.** TwinCAT's LD and
FBD paths have been examined far less closely than CODESYS's — the `???` marker work, the network-text format and
the graphical round-trip evidence were all developed against CODESYS and only pointed at TwinCAT afterwards,
which is exactly how four of these five surfaced in a single run. So a row here saying "TwinCAT does X" is a
statement about what was measured, not proof that X is inherent. **If everything were correct the results would
be identical**; each row is therefore a defect until someone shows the vendor genuinely cannot express the shape,
and grouping is the first place to dig, since it is the one that changes the body without saying so.

**One of these was silent data loss until 2026-09-05, and it was not the `???` case.** A fully resolvable
`ET => el` was dropped on create and the push reported success: TwinCAT's importer left the box's `OutputItems`
empty, the repair that strips the importer's *own* empty-operand artifact could not tell that empty slot from a
real pin, and the in-place writer's refusal that followed was swallowed by a `catch` whose premise ("nothing to
lose") was false. That is fixed — the order is now stamp-then-repair, and an output pin counts as content — so
the push refuses instead. **Refusing is not the destination.**

## What Changes

Close all four, so no e2e test needs a vendor branch.

**One route plausibly covers all four**, and it is already the shape of the code: PLCopen is how TwinCAT accepts
a body it does not have, and `TcNetworkWriter` is how Volt edits a body it does. Nothing today combines them.
Import the part PLCopen *can* state, then use the archive writer to set what it cannot — the same in-place edit
that already works on a pulled body carrying these shapes. Measured facts that make this look reachable:

- an embedded output pin can be **edited** on both vendors today (`TcNetworkWriter.WriteBoxOutputs`); only
  creating one has no route
- the importer *does* honour the `outVariable` wire — it produces a `BoxTreeAssign`, so the operand survives the
  import and the question is whether it can be moved onto the box's own slot rather than rebuilt
- the EN refusal is about the importer FOLDING the enable, not about the archive being unable to hold one

**What must not be done to close them**: build archive elements from a template. Twenty `.TcPOU` files were once
made unopenable that way, `BoxTreeBox` has no concrete class in any shipped assembly (DIALECT N11), and the
whole reason the create path goes through PLCopen is that the IDE must resolve what Volt does not model.

## Impact

- `packages/volt-cli/src/Volt.Ide.Twincat/Ide/TcPlcOpenWriter.cs` — the four refusals
- `packages/volt-cli/src/Volt.Ide.Twincat/Ide/TcNetworkWriter.cs` — the post-import edit
- `packages/volt-cli/src/Volt.Ide.Twincat/Driver/BeckhoffDriver.Content.cs` — `Stamp`, where import and edit meet
- `packages/volt-cli/test/e2e/graphical/{roundtrip,unresolved-marker,create-shapes}.test.ts` — every vendor
  branch here is deleted when its shape lands, and that deletion is the definition of done

**Done = the e2e suite has no `VENDOR === "twincat"` branch left in `test/e2e/graphical/`, and the full suite is
green on both vendors.** Each branch carries the refusal text it asserts, so it is obvious which one to delete.
