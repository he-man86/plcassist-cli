## Why

**A migrated project builds differently from the one it came from, and the code is identical.**

`Project Settings.projectsettings` is a read-only descriptor. pro2193's says:

```
Disabled warnings:     C0371
Replace constants:     on
Max compiler warnings: 100
```

None of that travels. Push pro2193 into a blank project and the target keeps ITS settings, so the same source
compiles under a different warning configuration - C0371 fires in one and not the other. The LSP reads the same
file to gate option-dependent checks, so its diagnostics diverge too. **"The build and the LSP agree between the
source project and the migrated one" is not reachable while compiler settings stay behind**, and that is the bar
this repo has set for a migration.

**And it is worse than "not writable": it is not reliably READABLE.** `scripts/probe-projectsettings8.py`
measured why - `ProjectSettingsDescriptor` reads
`APEnvironment.LMServiceProvider -> ConfigurationService -> WarningConfiguration`, which is a **session-global
singleton, not a property of the node being described**. Pulled from a headless session it answered "no disabled
warnings" for a project whose build proves C0371 is off. So a fresh headless pull would write the WRONG settings
into the workspace, and a push built on that would carry them into the engineer's project.

**Order matters here.** Making the descriptor writable before the read is trustworthy would take a value Volt
misread and write it back - the worst possible outcome, and one a round-trip test would call success because the
two halves agree with each other.

## What Changes

- **Fix the READ first.** Establish, live, how to reach a PROJECT's warning/compile configuration rather than the
  session's - or establish that the singleton is genuinely correct once a project is loaded and the headless
  reading was an artifact of something else. Record the answer in `Ide/DIALECT.md` either way.
- **Then make `.projectsettings` writable**, joining `ItemKind.WritableReferenceKinds` alongside `task`, with the
  same shape: the engine owns the file FORMAT (`Format/...`), each driver owns only the vendor call.
- **TwinCAT gets an answer too** - either it writes the equivalent, or it REFUSES a pushed setting it cannot
  express, by name, the way `TcTaskSchedule` refuses `Type: Freewheeling`. `VendorCapabilityParityTests` and
  `TaskSettingsAreFullyWrittenTests` are the gates that make a silent one-vendor capability impossible.
- **The migration finder starts comparing settings**, which it excludes today for the honest reason that they
  belong to the target project. Once they travel, they are part of what must round-trip.

## Impact

- `packages/volt-cli/src/Volt.Ide.Codesys/Ide/CodesysObjectModel.Descriptors.cs` (the read, then the write)
- `packages/volt-cli/src/Volt.Engine/Item/ItemKind.cs` (`WritableReferenceKinds`)
- `packages/volt-cli/src/Volt.Engine/Format/` (a settings format, the `Format/Task` twin)
- `packages/volt-cli/src/Volt.Ide.Twincat/` (write or a named refusal)
- `packages/volt-cli/scripts/corpus-migration.ts`, `packages/volt-lsp-iec` (option-gated checks)
