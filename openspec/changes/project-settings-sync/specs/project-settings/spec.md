## ADDED Requirements

### Requirement: A project's compiler settings are read correctly or not at all

The bridge SHALL report the compiler settings OF THE PROJECT it is serving. Where it cannot determine them, it
SHALL say so rather than emit defaults, because a settings file is indistinguishable from a correct one once
written, and a push built on it carries the wrong configuration into the engineer's project.

The vendor's configuration is reached through a SESSION-global service
(`APEnvironment.LMServiceProvider -> ConfigurationService`), not through the node being described - measured
2026-09-04, where a headless session reported "no disabled warnings" for a project whose build proves `C0371`
is disabled.

#### Scenario: settings read in any session match the project
- **WHEN** a project is pulled, headless or with the IDE's GUI
- **THEN** the emitted `.projectsettings` matches what that project's build actually uses

#### Scenario: an unknowable setting is not reported as a default
- **WHEN** the bridge cannot determine a setting for the project it is serving
- **THEN** the descriptor states that
- **AND** it does NOT report the vendor's default as though it were the project's value

### Requirement: Compiler settings travel with a migration

`.projectsettings` SHALL be pushable, so a project pushed into an empty one compiles under the configuration it
was written for. Without this the same source compiles differently in source and target, and the difference is
invisible in the code - the LSP reads the same file to gate option-dependent checks, so its diagnostics diverge
with the build's.

#### Scenario: a migrated project builds like its source
- **WHEN** a project whose settings disable a warning is migrated into an empty project
- **THEN** the target's settings match the source's
- **AND** the build diagnostics of the two projects agree

#### Scenario: a vendor that cannot express a setting refuses it by name
- **WHEN** a settings file carrying a value a vendor cannot express is pushed
- **THEN** the push is REFUSED naming the setting
- **AND** it is NOT accepted and silently ignored

#### Scenario: a settings field that reaches no driver fails the build
- **WHEN** a field is added to the settings format and a vendor's write path never reads it
- **THEN** a repo gate fails naming the field and the vendor
