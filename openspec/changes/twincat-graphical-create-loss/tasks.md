# Tasks

**Task 1 is the refusal, not the lowering.** Landing a partial body while reporting success is the failure that
makes every other one invisible; a loud refusal is correct behaviour even if the lowering is never improved.

## 1. Make the failure loud

- [ ] Reproduce offline: build the model from `fixtures/tc-workspace/ladderLabel.prg`, drive `Stamp` with a
      `built` archive of ONE network, and assert the `NotSupportedException` propagates. `CarriesDetail` is
      true for this model, so it should — find out why it does not on the live path.
- [ ] Fix it, and gate it: a create whose result has fewer networks than the model, or loses a label the model
      carries, FAILS the push.
- [ ] Verify live: the same one-file corpus that found this reports a REFUSAL, not a clean migration.

## 2. Decide what the lowering should carry

- [ ] The DECLARATION: `<interface />` is emitted empty. Establish whether the importer would honour a populated
      one — the scratch POU only needs it to resolve calls, so this may be correct as it stands and the real
      loss is elsewhere in `WriteOne`.
- [ ] The VIEW MODE: the document says `<FBD>` for an LD model, and `TcArchive.WithViewMode` is supposed to
      correct it after the import. Measure which half is wrong.
- [ ] LABELS: absent from the document. `Stamp` is meant to write them back after the import; it cannot reach a
      network that was never built.
- [ ] An EMPTY network is forced (D25 — PLCopen has no network element). Refuse it by name; do not invent one.

## 3. Close the loop

- [ ] `twincat-project14` migrates with no drift, or every remaining difference is a NAMED refusal.
- [ ] The offline tests fail without each fix, verified by breaking each one.
