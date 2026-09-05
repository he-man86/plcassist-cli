# Tasks

Each shape is done when its e2e vendor branch is DELETED and the test passes on both vendors. Nothing here is
done by widening a refusal or skipping a test.

## 0. Establish the route (do this first — it decides the other four)

- [ ] Push `t1(IN := a, PT := pt, ET => el)` with the `outVariable` emission restored (it is in the history of
      `TcPlcOpenWriter`, removed in the same commit that added the refusal) and DUMP the resulting archive.
      The question is exactly one: does the box carry an `OutputItems` slot for `ET`, with the operand on the
      separate `BoxTreeAssign` — or is there no slot at all?
- [ ] If a slot exists: the fix is to move the operand onto it and drop the assign item, which is a VALUE edit
      of the kind `TcNetworkWriter` already does. If no slot exists, say so here and the route is dead — record
      what replaces it before writing code.
- [ ] Either way, write the finding into DIALECT (C20 is the placeholder) with the archive fragment.

## 1. Embedded output pin — `t1(… ET => el)`

- [ ] Import + post-import edit, per task 0.
- [ ] Delete the branch in `create-shapes.test.ts` ("a box's embedded OUTPUT pin survives a create").
- [ ] Delete the two branches in `unresolved-marker.test.ts` (`qmark_out`, `qmark_both`) — they are the same
      limit reached through `???`, and they pass for free once the pin does.

## 2. Unconnected input pin — `FB(xEnable := , Axis := )`

- [ ] Import with the pin wired to something the importer accepts, then CLEAR the operand through the archive
      writer (an empty operand is a shape the vendor's own editor produces, so this is not element construction).
- [ ] Delete the branch in `unresolved-marker.test.ts` (`qmark_lib`).

## 3. Wired EN input

- [ ] Import the box WITHOUT the enable, then set the EN wire through the archive writer. The existing refusal
      is about the importer folding an enable into the box as an ordinary input — it is not a claim that the
      archive cannot hold one.
- [ ] Verify the folded-input failure mode is really gone: `IF en THEN out := (a AND b)` must not come back as
      `out := (en AND a AND b)`.
- [ ] Delete the branch in `unresolved-marker.test.ts` (`qmark_coilen`).

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
