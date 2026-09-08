# Tasks

Done means the finder RUNS on TwinCAT and its result is believed — not that it was pointed at TwinCAT and
skipped. A vendor branch or an early return is the failure mode this change exists to remove.

## 0. What is already true (2026-09-08)

- [x] The shared ST layer is green on both vendors LIVE: e2e 175 pass / 20 skip / 0 fail on CODESYS **and**
      TwinCAT, after both drivers moved from `.Trim()` to `TrimEnd('\n')` on every declaration and body they read.
- [x] `ConnectorSetup.TwincatExe()`'s dev-build fallback path fixed — it resolved to
      `packages/volt-cli/volt-cli/src/…`, so TwinCAT was undetectable in a dev build and the probe failed
      silently. This is why "nothing routinely drives TwinCAT" was true in practice.
- [ ] Nothing below.

## 1. A blank TwinCAT project

- [ ] Decide what "empty" IS for TwinCAT. CODESYS copies a shipped `Standard.project`; TwinCAT has no template
      to copy. Candidates: a committed empty solution under `test/fixtures/`, or one created through the DTE.
      Whichever it is, the target must start empty EVERY run — the CODESYS path copies per corpus for exactly
      that reason.
- [ ] Record the answer in `Ide/DIALECT.md`. "There is no blank-project template" is a vendor fact, not a note.
- [ ] Wire it as a `Blank` in `corpus-migration.ts` beside `CODESYS`. Open through `twincat-instances.ps1`,
      wait for the pipe, close it again.

## 2. Run it, and believe the result

- [ ] `VOLT_VENDOR=twincat bun run scripts/corpus-migration.ts <corpus>` reaches the comparison — not the
      "no blank-project launcher" throw.
- [ ] Every drift it reports is triaged the way the CODESYS ones were: a gap gets a fix and an OFFLINE test in
      `volt-cli` that fails without it. The corpus run is a finder, never the standing coverage.
- [ ] Expect the importer's grouping (D25) to show up here as reshaped bodies. That is a KNOWN vendor
      difference, and the finder must be able to say so without being taught to ignore drift in general.

## 3. TwinCAT evidence for the ST layer

- [ ] Pull a real TwinCAT project and run the `VOLT_CORPUS` sweep in `StFixedPointTests` over it. Today every
      one of the eight fixtures and all five corpora are CODESYS pulls, so the fixed-point invariant has never
      been tested against a TwinCAT tree.
- [ ] Commit any boundary shape the TC archive produces that a CODESYS pull does not, as a fixture. **If there
      are none, record that** — "measured, no TwinCAT-specific shapes" is a result; assuming it is not.
- [ ] Commit one TwinCAT corpus under `test-corpus/` so the LSP gates have TC input at all.

## 4. Close the loop

- [ ] `test/Volt.Ide.Twincat.Tests` gains at least one test that reaches `StReader`/`StWriter` through the
      Beckhoff driver, so a regression in the shared format layer cannot stay green on the TwinCAT side.
