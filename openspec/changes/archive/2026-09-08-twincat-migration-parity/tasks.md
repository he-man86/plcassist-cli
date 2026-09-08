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
- [x] Every drift it reports is triaged the way the CODESYS ones were. The run reports two things and both are
      accounted for: `POUexecute.prg` REFUSED (C20, named — see below), and `ladderLabel.prg` DRIFTED, which is
      a real data-loss bug and is tracked as its own change, **`twincat-graphical-create-loss`**. Isolated to a
      one-file corpus first, so neither the other items nor the refusal-recovery is involved: a graphical POU
      created in an empty TwinCAT project loses its declaration, its language (LD → FBD), both network labels,
      its coil and an entire network — while `volt push` reports success. Half of it is measurable offline
      (the PLCopen lowering emits an empty `<interface/>`, an `<FBD>` body for an LD model, one network of two,
      and no labels), and the guard that should have refused it (`Stamp`'s `CarriesDetail`/`LostNetworks`) did
      not fire, which is that change's first task.
- [x] Expect the importer's grouping (D25) to show up here, and say so without learning to ignore drift in
      general. The finder now recovers from a push the bridge refuses BY NAME: it drops that item, re-stages,
      pulls what already landed, and pushes the rest — reporting each as a `refused` line beside the `adapted`
      ones. Deliberately narrow: a failure it cannot parse an item name out of is rethrown untouched, because
      a finder that shrinks its own input until the push succeeds would report a clean migration of nothing.
      Without it TwinCAT stopped at item 7 of 9 and the other eight were never compared — which is how
      `ladderLabel.prg`'s loss stayed invisible.

## 3. TwinCAT evidence for the ST layer

- [x] Pull a real TwinCAT project and run the `VOLT_CORPUS` sweep in `StFixedPointTests` over it. **Clean over
      10 source files** (the corpus's other 237 are rendered `References/` signatures). The sweep now REPORTS
      its coverage — 10 here against 535 for pro2193 — because `checkedCount > 0` cannot tell 10 files from 900
      and both pass in under a millisecond.
- [x] Commit any boundary shape the TC archive produces that a CODESYS pull does not. **One found, and it took
      the right input to find it.** Over the corpus's 10 member-less files there is no TwinCAT-specific shape.
      Push a POU that HAS a method and a property, though, and TwinCAT hands back a blank line between the SET
      accessor's `END_VAR` and its body — and none in the GET, from identical pushed text (DIALECT D33, stable,
      cosmetic). Committed as `FB_VltMembers.fb`: pushed into a live scratch project and pulled back in a fresh
      workspace, so the bytes are the IDE's rather than the ones that were sent.
      Two TwinCAT-authored files are committed as fixtures anyway (`fixtures/tc-workspace/`), because the
      corpus sweep is opt-in behind `VOLT_CORPUS` and never runs in CI. `ladderLabel.prg` does carry two
      network-level shapes no hand-written fixture had: a network whose LABEL is its only content, and a coil
      with nothing driving it (`coil := ;`, read back as the terminator the archive holds).
      **The member gap this exposed is now closed**: no TwinCAT corpus file declares a METHOD, ACTION or
      PROPERTY, so member splitting had no TwinCAT-sourced evidence at all until that POU was pushed and
      pulled back.
- [x] Commit one TwinCAT corpus under `test-corpus/` so the LSP gates have TC input at all. **`twincat-project14`**;
      corpus gates 20 → 22.

## 4. Close the loop

- [x] `test/Volt.Ide.Twincat.Tests` gains a test that reaches `StReader`/`StWriter` — `TcSharedFormatTests`,
      driving TwinCAT-authored text through the shared ST layer and a TwinCAT-drawn ladder through
      `NetworkTextGate`. Verified live: a one-character regression in `StWriter`'s body separator fails 2 of
      its 3 cases (and 6 in the engine's own), so it is a gate and not decoration.
