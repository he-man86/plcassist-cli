# twincat-graphical-create

## ADDED Requirements

### Requirement: A create that cannot carry the pushed body SHALL fail the push

When TwinCAT's PLCopen import resolves a graphical body that does not match the pushed model, Volt SHALL refuse
the push rather than write the partial result and report success.

#### Scenario: a network the importer did not build

- **GIVEN** a pushed body of two networks, one of them empty apart from its label
- **WHEN** the PLCopen import returns one network
- **THEN** the push fails, naming the networks that could not be created
- **AND** the IDE is not left holding a body that claims to be the pushed one

#### Scenario: metadata the model carries and the result does not

- **GIVEN** a pushed network carrying a `LABEL`, `TITLE`, `COMMENT` or `DISABLED`
- **WHEN** the created body comes back without it
- **THEN** the push fails rather than dropping it silently
