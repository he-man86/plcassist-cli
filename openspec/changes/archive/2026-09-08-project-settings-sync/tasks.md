# Tasks

> **CLOSED 2026-09-08 — see `CLOSEOUT.md`.** Task 1 is done and its answer removed the reason for 2 and 3;
> `.projectsettings` stays READ-ONLY by decision. Sections 2 and 3 are left here unticked on purpose: the
> migration gap they address is real and still open, and this is the record of what it would take.

**The read is task 1 and it is not optional.** Writing back a value Volt misread is worse than not writing it,
and a round-trip test cannot catch it - both halves would agree with each other and both would be wrong.

## 1. Make the read trustworthy

- [x] Reproduce the headless miss. **IT DID NOT REPRODUCE** — and that is the finding, not a skipped step.
      Headless, with pro2193 loaded, `Disabled warnings:` comes back `C0371`, matching the GUI-recorded corpus
      file. The task said "confirm it still holds before designing around it"; it does not hold, so there was
      nothing to design around. What DOES reproduce is the same read with NO project open, which answers
      `(null)` — the 2026-09-04 symptom, and an ordering artifact rather than a scope bug.
- [x] Find the per-PROJECT route, or prove there is none. **PROVEN SOUND** — one session service over
      per-project state; the 2026-09-04 headless reading was an ordering artifact (no project loaded).
      Original text: `ConfigurationService.WarningConfiguration` is
      session-global; the question is whether a loaded project populates it and the headless reading was an
      artifact of ordering (read before the load completed), or whether the project's own configuration lives
      somewhere else entirely.
- [x] Record it in `Ide/DIALECT.md` with the evidence, whichever way it goes. **DIALECT C24.**
- [x] A pull SHALL NOT emit a settings file it cannot vouch for. Already held: the only state the service
      cannot vouch for is "no project open", and `volt init` refuses that before a descriptor is built.
      Original text: If the value is unknowable in a session, the
      descriptor says so rather than reporting defaults as fact.

## 2. Make it writable

- [ ] `.projectsettings` joins `ItemKind.WritableReferenceKinds`.
- [ ] A `Format/` type owns the file layout for BOTH directions, as `TaskDescriptorFormat` does - so the
      round-trip is a property of one type, testable offline, rather than two halves that agree by inspection.
- [ ] The CODESYS write, MEASURED per field the way `probe-task-kind.py` measured `kind_of_task`: which are real
      setters, which take a vendor enum, which are accepted and ignored. Assume nothing.
- [ ] TwinCAT: write the equivalent, or refuse by name. Update `VendorCapabilityParityTests`.
- [ ] A `TaskSettingsAreFullyWrittenTests` twin, so a settings field that reaches no driver fails the build -
      the same silent-omission failure the task type had.

## 3. Prove it end to end

- [ ] `corpus-migration.ts` stops excluding `.projectsettings` and the corpora still migrate clean.
- [ ] A migrated project's BUILD DIAGNOSTICS match the source project's. This is the bar the change exists for,
      and it is the first time it can be asserted at all.
- [ ] The LSP's option-gated checks (C0371 and friends) agree between source and migrated project.
