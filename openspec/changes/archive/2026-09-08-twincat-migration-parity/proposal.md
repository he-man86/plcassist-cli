## Why

**Every bug found today was found on ONE vendor, and the layer they were found in is shared.**

`scripts/corpus-migration.ts` — pushing a real customer project into an EMPTY one, so every item is a CREATE —
is the finder that surfaced all of it: a localized task container (DIALECT C22), a task type that was never
written, drivers that trimmed leading whitespace off everything they read, and five ways `StReader`/`StWriter`
disagreed about where a declaration ends. It refuses to run on TwinCAT and says so in a comment:

```ts
// TwinCAT has no headless mode and no in-proc host, so its blank has to be opened through
// `twincat-instances.ps1` against an empty solution. Not wired yet — this refuses rather than skipping
// quietly, because a silent skip is how a vendor stays untested through a whole implementation.
```

That comment describes exactly what then happened. **`Volt.Engine.Format.St` is vendor-neutral and both drivers
took the same `TrimEnd('\n')` change, but the evidence for all of it is CODESYS-only**: all eight fixtures in
`test/Volt.Engine.Tests/fixtures/st-fixed-point/` and all five `VOLT_CORPUS` projects are CODESYS pulls, and
`test/Volt.Ide.Twincat.Tests` does not reference that layer at all. A regression in TwinCAT's boundary handling
would keep every suite green.

**The migration path is also where the vendors differ most.** A blank CODESYS project comes from a shipped
template; TwinCAT has none of that plumbing, no headless mode and no in-proc host. The one-sided finder is
therefore not a small gap — it is the whole create path, on the vendor whose importer already reshapes bodies
(D25 grouping) and refuses four graphical shapes CODESYS accepts.

**A related defect this turned up, already fixed:** `ConnectorSetup.TwincatExe()` resolved its dev-build fallback
to `packages/volt-cli/volt-cli/src/Volt.Ide.Twincat` — a path that cannot exist, left over from when the
connector was its own package. `TwincatXaeProbe` returns null for a missing exe, null means "the probe FAILED"
rather than "no XAE", and a failed probe deliberately leaves the fleet untouched — so **TwinCAT was undetectable
in any dev build, silently, with nothing in the log.** That it went unnoticed is itself evidence for this change:
nothing routinely drives TwinCAT.

## What Changes

- **`corpus-migration.ts` grows a TwinCAT `Blank`** — open an empty solution through `twincat-instances.ps1`,
  serve it, and run the same two-push migration (empty, then create-everything) the CODESYS path runs.
- **A TwinCAT corpus.** At least one project pulled from a live XAE, committed under `test-corpus/`, so the
  `VOLT_CORPUS` fixed-point sweep and the LSP corpus gates have TwinCAT evidence at all.
- **TwinCAT-derived fixtures in `st-fixed-point/`** for any boundary shape the TC archive produces that a CODESYS
  pull does not. If there are none, that is a result worth recording rather than an assumption worth keeping.
- **The blank-project asymmetry gets written down** in `Ide/DIALECT.md` — what "an empty project" even means on a
  vendor with no template.

## Impact

- `packages/volt-cli/scripts/corpus-migration.ts`, `scripts/twincat-instances.ps1`
- `packages/volt-cli/test/Volt.Engine.Tests/fixtures/st-fixed-point/`
- `packages/volt-lsp-iec/test-corpus/`
- `packages/volt-cli/src/Volt.Engine/Ide/DIALECT.md`
