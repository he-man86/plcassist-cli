# Tasks

**Task 1 is the refusal, not the lowering.** Landing a partial body while reporting success is the failure that
makes every other one invisible; a loud refusal is correct behaviour even if the lowering is never improved.

## 0. A LEAD, measured 2026-09-08 — read before diagnosing

The same shape pushed ON ITS OWN is refused correctly. `test/e2e/graphical/uncovered-shapes.test.ts` creates a
POU whose network 0 holds an undriven coil and whose network 1 is empty and labelled — `ladderLabel.prg`
reduced to its two constructs — and TwinCAT REFUSES it by name:

    the number of networks changes (1 -> 2), which Volt cannot do through the archive

So `Apply`'s count guard fires, and `Stamp` propagates it, on the isolated push. The migration pushed the same
POU and was ACCEPTED. Whatever differs between those two paths is the bug, and it is a much smaller search than
"why is the guard silent": the guard is not silent, it is not being reached.

Differences worth eliminating first: the migration creates the POU alongside eight other items in one push, and
into a project the previous push had just emptied.

## 1. Make the failure loud

- [x] Reproduce offline: build the model from `fixtures/tc-workspace/ladderLabel.prg`, drive `Stamp` with a
      `built` archive of ONE network, and assert the `NotSupportedException` propagates. `CarriesDetail` is
      true for this model, so it should — find out why it does not on the live path.
- [x] Fix it, and gate it: a create whose result has fewer networks than the model, or loses a label the model
      carries, FAILS the push.
- [x] Verify live: the same one-file corpus that found this reports a REFUSAL, not a clean migration.

> **Section 2 is answered by the diagnosis, not by work on the lowering.** Every symptom listed there — the
> empty `<interface/>`, the `<FBD>` element for an LD model, the single network, the missing labels — is what
> the SCRATCH document looks like on its way to being refused. It is never adopted: the import is verified, the
> count mismatch is caught, and the push stops. The lowering does not need to carry any of it, because a body
> it cannot express is refused rather than written. What was broken was that the refusal left a shell behind.

## 2. Decide what the lowering should carry

- [x] The DECLARATION: `<interface />` is emitted empty. Establish whether the importer would honour a populated
      one — the scratch POU only needs it to resolve calls, so this may be correct as it stands and the real
      loss is elsewhere in `WriteOne`.
- [x] The VIEW MODE: the document says `<FBD>` for an LD model, and `TcArchive.WithViewMode` is supposed to
      correct it after the import. Measure which half is wrong.
- [x] LABELS: absent from the document. `Stamp` is meant to write them back after the import; it cannot reach a
      network that was never built.
- [x] An EMPTY network is forced (D25 — PLCopen has no network element). Refuse it by name; do not invent one.

## 3. Close the loop

- [x] `twincat-project14` migrates with no drift, or every remaining difference is a NAMED refusal.
- [x] The offline tests fail without each fix, verified by breaking each one.
