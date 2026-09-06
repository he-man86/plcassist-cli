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

## 4. Execute box (ST inside FBD) — CLOSED as not creatable, and it FAILS SILENTLY

- [x] Measured: emitted as a `<block typeName="EXECUTE">`, the importer ACCEPTS the push and returns
      `EXECUTE();` — a plain box whose TYPE NAME is the string EXECUTE, with the ST gone entirely. PLCopen FBD
      has no element for ST-in-a-box, and a type name is not enough.
- [x] That makes the refusal load-bearing rather than cautious: without it a push would report success and drop
      the engineer's code, which is the worst outcome of the five shapes.
- [x] Task 3 (EN) landed first, as required — the fixture is EN-guarded, so the enable now passes and the
      Execute box is the only wall left in it.
- [x] Vendor branch REMAINS in `roundtrip.test.ts`, and its assertion now accepts ONLY the Execute message
      (the EN alternative it allowed is dead).
- [x] READING one is DONE 2026-09-06, from a network drawn by hand in XAE
      (`test/Volt.Ide.Twincat.Tests/fixtures/tc-pou/execute-box.TcPOU`). It was a FIELD gap, not a test gap:
      `ReadStCode` refused outright, so an engineer with an Execute box could not pull the POU at all. Two members
      of the walk are guessable wrongly and both are now pinned by test — `TextLines` is an `<a>` ARRAY, not the
      `<l2>` every other member uses (wrong accessor ⇒ EMPTY, a box with no code), and each line's `Text` is
      stored WITH its own surrounding double quotes.
- [x] EDITING that ST is REFUSED, and had to be: nothing in `TcNetworkWriter` looked at `StCode`, so making the
      box readable created a silent-loss path — the push found no storage change, wrote nothing, reported SUCCESS
      and the next pull reverted the edit (the `JMP` retarget bug's exact shape). Test is red without the guard.
- [ ] Writing the ST back needs the `TextLine.Id` contract measured on a live XAE: a changed LINE COUNT means
      constructing `TextLine` items with invented ids, which is N11. Refusal until then.

## 4b. Network grouping — MEASURED, and the obvious repair CORRUPTS

- [x] Attempted the repair: merge the importer's split networks back into one by moving tree elements between
      existing lists (the same "move, never construct" reasoning that made the EN fix safe). It WORKS for
      independent rungs — all four grouping shapes came back as `[1,1,1,1]`, matching CODESYS exactly.
- [x] **And it corrupts a body whose trees reference each other.** `t1(IN := a, PT := pt); done := t1.Q;` came
      back as `done := ();` — the read of the box's output lost its target. So the importer's networks are NOT
      independent documents that merely got split: a tree in the second network can point into the first, and
      recombining them breaks that. Reverted.
- [ ] The divergence therefore stands for now, and it is the only one in this change that is neither a refusal
      nor a measured impossibility. Next avenue: find what the second network's tree actually references (a
      connection id? a demux?) and whether that reference can be rewritten as part of the move. Until then a
      split body is still a silent reshape, which is why this stays open rather than being written off.
- [ ] Vendor branch REMAINS in `graphical/grouping.test.ts`.

## 5. Close

- [ ] `grep -rn 'VENDOR === "twincat"' packages/volt-cli/test/e2e/graphical/` returns nothing.
- [x] Full e2e green on BOTH vendors, and the counts match: the same number of tests passing, not one vendor
      quietly running fewer. **2026-09-06: 186 pass / 8 skip / 0 fail, 194 tests, IDENTICAL on both** (graphical
      alone: 78/0 each). The only remaining asymmetry is the expect() count — 1185 CODESYS vs 1143 TwinCAT — and
      that difference IS the four vendor branches above, so it goes to zero when they do.
