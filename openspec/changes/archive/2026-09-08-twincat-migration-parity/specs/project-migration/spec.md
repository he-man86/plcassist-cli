## ADDED Requirements

### Requirement: A real project migrates into an empty project on EITHER vendor

The migration finder SHALL be runnable against both CODESYS and TwinCAT, and SHALL compare what comes back
against what was pushed on both. A vendor the finder cannot run against is a vendor whose CREATE path is
untested, and the create path is where the item-by-item bugs live: every defect the finder found on 2026-09-08
(a localized task container, an unwritten task type, drivers trimming leading whitespace, and five decl/impl
boundary disagreements) was a create-path defect in code shared by both vendors.

#### Scenario: the finder runs on TwinCAT
- **WHEN** the migration finder is asked to migrate a corpus with `VOLT_VENDOR=twincat`
- **THEN** it opens an empty TwinCAT project, pushes every writable item into it, materializes the result and
  reports the differences
- **AND** it does NOT refuse with "no blank-project launcher"

#### Scenario: a vendor that cannot be run is a failure, not a skip
- **WHEN** a vendor's blank-project launcher is missing or fails
- **THEN** the finder exits non-zero saying so
- **AND** it does NOT report success for the corpora it did manage to run

#### Scenario: a known vendor reshape is named, not absorbed
- **WHEN** TwinCAT's importer regroups a pushed body by connected component (DIALECT D25)
- **THEN** the finder reports it as that known difference
- **AND** the finder does NOT stop reporting drift in general to accommodate it

### Requirement: The shared source format has evidence from both vendors

The round-trip invariant of `Volt.Engine.Format.St` SHALL be tested against text pulled from BOTH vendors.
That layer is vendor-neutral and is reached through both drivers, so fixtures and corpora drawn from one vendor
prove that vendor's shapes only - and a regression in the other's boundary handling would leave every suite
green.

#### Scenario: the fixed-point sweep covers a TwinCAT tree
- **WHEN** the `VOLT_CORPUS` sweep in `StFixedPointTests` is pointed at a TwinCAT pull
- **THEN** every file satisfies `Write(Read(x)) == x`

#### Scenario: a TwinCAT-only boundary shape becomes a committed fixture
- **WHEN** a TwinCAT pull produces a declaration/body boundary shape no CODESYS pull produces
- **THEN** that shape is committed as a fixture in `st-fixed-point/`
- **AND** if no such shape exists, that measurement is recorded rather than assumed
