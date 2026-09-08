# Close-out — the read was the whole risk, and it turned out to be sound

Closed 2026-09-08. Task 1 was DONE and its answer removed the reason for tasks 2 and 3; the remaining scope was
then dropped by decision — **`.projectsettings` stays read-only.**

## What task 1 asked, and what it found

The change existed because of a doubt with real teeth. `ProjectSettingsDescriptor` reads
`APEnvironment.LMServiceProvider -> ConfigurationService -> WarningConfiguration / CompileOptions`, and that
provider is a **singleton on the engine, not a property of the node being described** — so project A's
descriptor might be reporting whatever project B last left there. A 2026-09-04 headless probe appeared to
confirm it: pro2193 came back with no disabled warnings when its build proves `C0371` is off.

**Measured properly, the read is correct.** `scripts/probe-projectsettings-scope.py` →
`scripts/projectsettings-scope.log`, recorded as DIALECT **C24**.

The experiment is a SWITCH, not a single read, over a corpus pair that disagrees in two independent fields:

| stage | Disabled warnings | UTF-8 encoding |
|---|---|---|
| no project open | `(null)` | off |
| **A** — `Pro2193_COdesys` | **C0371** | off |
| A closed | `(null)` | off |
| **B** — `CodesysTestProject` (A was open before it) | `(null)` | **on** |
| **A again** (B was open before it) | **C0371** | off |

Both fields track the loaded project, in both directions, across a switch — while the service OBJECT stays the
same instance at every stage (`ConfigurationService#135`). One session service, per-project state.

**And the headless miss is explained rather than reproduced.** With no project open the service answers
`(null)` and defaults — exactly the symptom the 2026-09-04 probe reported. That reading was an ORDERING
artifact (read before, or without, the load), not a scope bug. This run was itself headless, and headless reads
correctly once a project is loaded.

The proposal's own task list allowed for this outcome — *"or establish that the singleton is genuinely correct
once a project is loaded and the headless reading was an artifact of something else"* — which is what happened.

## Why tasks 2 and 3 are dropped rather than pending

They exist to close a migration gap: a project pushed into a blank one keeps the TARGET's compiler settings, so
the same source can build under a different warning configuration. That gap is real and is NOT fixed by this
close-out. It is simply not being paid for with a writable descriptor.

`.projectsettings` stays a read-only descriptor. Volt reports the project's compiler configuration faithfully —
which is now measured, not assumed — and does not write it.

## What is in the tree from this change

- `Ide/DIALECT.md` **C24** — the measurement, with its evidence.
- `scripts/probe-projectsettings-scope.py` + `scripts/projectsettings-scope.log` — the probe and its answer.
- `CodesysObjectModel.ProjectSettingsDescriptor`'s comment, which stated the doubt and now states the finding.

No product behaviour changed. The descriptor reads exactly as it did; what changed is that it is now known to
be right.

## What is still true and still unaddressed

**A migrated project can build differently from the one it came from.** Compiler settings do not travel, so
`C0371` fires in the target and not the source, and the LSP's option-gated checks diverge with them. The
migration finder still excludes `.projectsettings` for that reason.

If that is ever taken up, task 1 is already done — the read can be trusted — and the work starts at
`ItemKind.WritableReferenceKinds` with a `Format/` type owning the layout, the way `TaskDescriptorFormat` does.
The per-field CODESYS write is still unmeasured, and TwinCAT still needs either an equivalent or a named
refusal.
