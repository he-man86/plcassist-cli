# Tasks

Done means the finder RUNS on TwinCAT and its result is believed — not that it was pointed at TwinCAT and
skipped. A vendor branch or an early return is the failure mode this change exists to remove.

## 0. What is already true (2026-09-08)

- [x] The shared ST layer is green on both vendors LIVE: e2e 175 pass / 20 skip / 0 fail on CODESYS **and**
      TwinCAT, after both drivers moved from `.Trim()` to `TrimEnd('\n')` on every declaration and body they read.
- [x] `ConnectorSetup.TwincatExe()`'s dev-build fallback path fixed — it resolved to
      `packages/volt-cli/volt-cli/src/…`, so TwinCAT was undetectable in a dev build and the probe failed
      silently. This is why "nothing routinely drives TwinCAT" was true in practice.

## 0b. MEASURED on the first live run (2026-09-08) — read before designing

Four failures, in order, each one moving the boundary forward. The first three are FIXED; the fourth reframes
the change.

- [x] `twincat-instances.ps1` corrupted its own pid file: `$live + $pids` does STRING concatenation when
      `Get-Content` returns a scalar (a one-line file), writing `"22620" + 10388` = a pid too big for Int32.
      `down` then threw on binding and closed NOTHING — ten orphaned TcXaeShell windows accumulated unnoticed.
- [x] A TwinCAT XAE starts every project IDLE and must be TOLD which to serve; `volt init` failed with "the
      bridge has no PLC project loaded". In production the CONNECTOR selects when a client declares an interest,
      so a finder — which has no session — selects directly over the pipe.
- [x] `deviceRoot()` asserted a CODESYS shape and threw `found 0`. It is optional now.
- [x] **DIALECT N15: a TwinCAT workspace has NO device root.** `src/POUs/…`, with `PlcTask.task`,
      `External Types.external_types`, the `.tmc` and `References/` as siblings at the top — where CODESYS has
      three structural levels (`<Device>/Plc Logic/Application`) before the first user item.

**Which reframes the goal.** `Device/Plc Logic/Application/99 Library/Round.fun` has NO TwinCAT counterpart, so
pushing a CODESYS corpus into a TwinCAT project is a PATH TRANSLATION — cross-vendor migration, a different and
much larger feature than the same-vendor create-path coverage this finder exists for. **TwinCAT needs a
TwinCAT-sourced corpus**, and until it has one the finder cannot be pointed at this vendor meaningfully. Task 3
is therefore a PREREQUISITE for task 2, not a follow-on.

## 1. A blank TwinCAT project

- [x] Decide what "empty" IS for TwinCAT. **A committed fixture solution, copied per run.** CODESYS copies a
      shipped `Standard.project`; TwinCAT ships no template, so the target is `test/fixtures/TwinCAT Project13`
      copied per corpus and emptied by its own first push — which is what makes it start empty EVERY run, the
      property the CODESYS path gets from copying the vendor's template.
- [x] Record the answer in `Ide/DIALECT.md`. **DIALECT N15** carries it: TwinCAT ships no template, so an
      "empty" target is a committed fixture copied per run and emptied by its own first push.
- [x] Wire it as a `Blank` in `corpus-migration.ts` beside `CODESYS`. Open through `twincat-instances.ps1`,
      wait for the pipe, close it again.

## 2. Run it, and believe the result

- [x] `VOLT_VENDOR=twincat bun run scripts/corpus-migration.ts <corpus>` reaches the comparison. It ran, got 6
      of 9 items in, and was refused on `POUexecute.prg` — TwinCAT cannot re-import an Execute box it authored
      itself (C20). A real result, not a throw.
- [ ] Every drift it reports is triaged the way the CODESYS ones were: a gap gets a fix and an OFFLINE test in
      `volt-cli` that fails without it. The corpus run is a finder, never the standing coverage.
- [ ] Expect the importer's grouping (D25) to show up here as reshaped bodies. That is a KNOWN vendor
      difference, and the finder must be able to say so without being taught to ignore drift in general.

## 3. TwinCAT evidence for the ST layer

- [x] Pull a real TwinCAT project and run the `VOLT_CORPUS` sweep in `StFixedPointTests` over it. **Clean over
      10 source files** (the corpus's other 237 are rendered `References/` signatures). The sweep now REPORTS
      its coverage — 10 here against 535 for pro2193 — because `checkedCount > 0` cannot tell 10 files from 900
      and both pass in under a millisecond.
- [x] Commit any boundary shape the TC archive produces that a CODESYS pull does not. **Measured: no
      TwinCAT-specific ST shape** — all 10 files round-trip against the same rules, on thin but real evidence.
      Two TwinCAT-authored files are committed as fixtures anyway (`fixtures/tc-workspace/`), because the
      corpus sweep is opt-in behind `VOLT_CORPUS` and never runs in CI. `ladderLabel.prg` does carry two
      network-level shapes no hand-written fixture had: a network whose LABEL is its only content, and a coil
      with nothing driving it (`coil := ;`, read back as the terminator the archive holds).
      **The gap that remains, measured rather than assumed:** not one TwinCAT corpus file declares a METHOD,
      ACTION or PROPERTY, so member splitting has no TwinCAT-sourced evidence anywhere.
- [x] Commit one TwinCAT corpus under `test-corpus/` so the LSP gates have TC input at all. **`twincat-project14`**;
      corpus gates 20 → 22.

## 4. Close the loop

- [x] `test/Volt.Ide.Twincat.Tests` gains a test that reaches `StReader`/`StWriter` — `TcSharedFormatTests`,
      driving TwinCAT-authored text through the shared ST layer and a TwinCAT-drawn ladder through
      `NetworkTextGate`. Verified live: a one-character regression in `StWriter`'s body separator fails 2 of
      its 3 cases (and 6 in the engine's own), so it is a gate and not decoration.
