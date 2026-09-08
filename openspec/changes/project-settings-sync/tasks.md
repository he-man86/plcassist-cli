# Tasks

**The read is task 1 and it is not optional.** Writing back a value Volt misread is worse than not writing it,
and a round-trip test cannot catch it - both halves would agree with each other and both would be wrong.

## 1. Make the read trustworthy

- [ ] Reproduce the headless miss: open pro2193 headless, pull, and confirm `Disabled warnings:` comes back
      EMPTY where the GUI-recorded corpus file says `C0371`. (Measured once, 2026-09-04, by
      `probe-projectsettings8.py`; confirm it still holds before designing around it.)
- [ ] Find the per-PROJECT route, or prove there is none. `ConfigurationService.WarningConfiguration` is
      session-global; the question is whether a loaded project populates it and the headless reading was an
      artifact of ordering (read before the load completed), or whether the project's own configuration lives
      somewhere else entirely.
- [ ] Record it in `Ide/DIALECT.md` with the evidence, whichever way it goes.
- [ ] A pull SHALL NOT emit a settings file it cannot vouch for. If the value is unknowable in a session, the
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
