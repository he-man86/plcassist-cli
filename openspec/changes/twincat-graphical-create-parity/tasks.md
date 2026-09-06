# Tasks

Each shape is done when its e2e vendor branch is DELETED and the test passes on both vendors. Nothing here is
done by widening a refusal or skipping a test.

## 0. Establish the route — ANSWERED 2026-09-06

- [x] Push `t1(IN := a, PT := pt, ET => el)` with the `outVariable` emission restored and see what the importer
      builds. **Answer: it ignores `formalParameter`.** The body came back as `el := t1(IN := a, PT := pt)` —
      the variable wired to the box's UNNAMED RESULT, not to `ET`.
- [x] Is there an `ET` slot to move the operand into? **No.** The archive holds a `BoxTreeAssign` from the box's
      result; the box has no output slot at all. So there is nothing to fix up after the import, and creating the
      slot would mean building archive members — the one thing the writer must not do (N11: `BoxTreeBox` has no
      concrete class in any shipped assembly, and inferring its member contract once produced twenty unopenable
      `.TcPOU` files).
- [x] Recorded in DIALECT C20 with the evidence.

**Consequence: the import-then-edit route is DEAD for a named output pin**, and the refusal is now evidence-based
rather than cautious. It is also worse than a reshape — a TON's result pin is `Q` (BOOL), so accepting what the
importer builds would assign a BOOL to a TIME variable and change what the program computes.

**This does not settle the other shapes.** Import-then-edit may still work where the shape survives the import
with its identity intact; the output pin fails because the PIN IDENTITY is what the importer discards. Each
remaining shape needs its own measurement before its refusal is called permanent.

## 1. Embedded output pin — `t1(… ET => el)` — CLOSED as not creatable

- [x] Measured (task 0): neither route reaches it. The refusal stays, and is now documented as measured.
- [ ] Keep the vendor branches in `create-shapes.test.ts` and `unresolved-marker.test.ts` (`qmark_out`,
      `qmark_both`) — they assert a REAL vendor limit, not a gap. Reword them to say "cannot", not "cannot yet".
- [ ] Delete the branch in `create-shapes.test.ts` ("a box's embedded OUTPUT pin survives a create").
- [ ] Delete the two branches in `unresolved-marker.test.ts` (`qmark_out`, `qmark_both`) — they are the same
      limit reached through `???`, and they pass for free once the pin does.

## 2. Unconnected input pin — `FB(xEnable := , Axis := )` — DONE 2026-09-06

- [x] Measured: emitted as an `<inVariable>` with an EMPTY expression, the importer builds exactly the right
      shape and `t1(IN := , PT := pt);` round-trips BYTE-IDENTICAL. The refusal was wrong — an empty operand is a
      shape the vendor's own archives already carry, so this is its spelling, not an invention.
- [x] `TcPlcOpenWriter` emits a BARE `Terminator` that way. One carrying an Input is a rung end feeding a value —
      a different shape with no measurement behind it — and keeps a refusal of its own.
- [x] Vendor branch DELETED from `unresolved-marker.test.ts` (`qmark_lib`). Graphical suite: 78 pass / 0 fail on
      BOTH vendors.

## 3. Wired EN input — DONE 2026-09-06

- [x] The importer folds a wired enable in as a DATA input (measured 2026-08-31: `IF en THEN out := (a AND b)`
      came back as `out := (en AND a AND b)`). That fold is REPAIRABLE: the input item and its name slot both
      exist, at slot 0, because the writer emits the enable first. `TcNetworkWriter` renames the slot to `EN` and
      sets the `En` display flag — two VALUE edits, no archive construction.
- [x] Verified the folded-input failure mode is gone: `IF en1 THEN out := (a AND b); END_IF` round-trips
      BYTE-IDENTICAL and the project COMPILES clean.
- [x] Vendor branch DELETED from `unresolved-marker.test.ts` (`qmark_coilen`). Graphical suite: 78 pass / 0 fail
      on BOTH vendors.
- [x] Narrow by construction: the repair only fires when the box has EXACTLY one input more than the model, the
      signature of the fold. Any other mismatch still refuses.

## 4. Execute box (ST inside FBD)

- [ ] The oldest of the four. PLCopen has no element; the CODESYS path builds `<block typeName="EXECUTE">` plus
      `<STCode>`. Determine whether TwinCAT's importer accepts that same block, and if not, whether an ordinary
      box can be imported and its `STCode` set through the archive writer.
- [ ] **Task 3 must land first.** The fixture is EN-guarded (`LET en1 := bRun; IF en1 THEN EXECUTE …`), so it
      hits the EN refusal BEFORE the Execute box is reached — fixing Execute alone will not turn this test
      green, and the assertion accepts either message for exactly that reason.
- [ ] Delete the branch in `roundtrip.test.ts` ("creates an FBD program with an Execute box").

## 4b. Network grouping — a silent reshape, not a refusal

- [ ] A body pushed as ONE network returns as N on TwinCAT (one per connected component). Decide whether the
      importer can be made to preserve the pushed grouping — the network boundary is Volt's, and the importer
      currently re-derives it.
- [ ] If it cannot: make it a stated REFUSAL like the other four, so the engineer is told rather than silently
      handed a different body. A measured, stable difference is still a difference.
- [ ] Delete the vendor branch in `graphical/grouping.test.ts` (`[1,1,2,2]` vs `[1,1,1,1]`).

## 5. Close

- [ ] `grep -rn 'VENDOR === "twincat"' packages/volt-cli/test/e2e/graphical/` returns nothing.
- [ ] Full e2e green on BOTH vendors, and the counts match: the same number of tests passing, not one vendor
      quietly running fewer.
