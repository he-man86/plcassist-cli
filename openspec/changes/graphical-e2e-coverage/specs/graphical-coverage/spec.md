# graphical-coverage

## ADDED Requirements

### Requirement: Every network-text construct SHALL be exercised against a live IDE or have a stated reason it cannot be

The e2e suite SHALL push each construct the network-text format defines, so that a construct's behaviour on a
real IDE is measured rather than assumed.

#### Scenario: a construct with no live coverage

- **GIVEN** a construct defined in `docs/network-text.md`
- **WHEN** no test in `test/e2e` pushes it
- **THEN** `scripts/e2e-graphical-coverage.ts` reports it as a GAP
- **AND** the gap is closed by a live test, or by a written reason the construct cannot be created

#### Scenario: a construct that a vendor cannot create

- **GIVEN** a construct one vendor's importer cannot express
- **WHEN** it is pushed
- **THEN** the push is refused BY NAME rather than landing a partial body
