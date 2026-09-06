## ADDED Requirements

### Requirement: A graphical body pushed to either vendor comes back as the body that was pushed

The bridge SHALL return, from a pull, the same graphical body a push sent — the same networks, the same boxes,
the same pins and the same operands — on BOTH vendors. Where a vendor's importer cannot build a shape, the push
SHALL be REFUSED with a message naming the shape, and SHALL NOT be accepted and silently reshaped.

The contract is one suite over two bridges: a pass on one and a fail on the other is a defect, not a vendor
property. TwinCAT's LD and FBD paths have had materially less scrutiny than CODESYS's — the network-text format,
the `???` marker work and the round-trip evidence were all developed against CODESYS and pointed at TwinCAT
afterwards — so each shape below is a defect until the vendor is shown genuinely unable to express it.

#### Scenario: an embedded output pin survives a create
- **WHEN** a body wiring a box's named output pin to a variable (`t1(IN := a, PT := pt, ET => el)`) is pushed to
  a vendor
- **THEN** the pin is present in the body read back
- **AND** if the vendor cannot place it, the push is refused naming the pin — never accepted with the pin missing

#### Scenario: an unconnected input pin survives a create
- **WHEN** a body carrying a genuinely unconnected input pin (`FB(xEnable := , Axis := )`) is pushed
- **THEN** it round-trips unchanged, or the push is refused with a reason

#### Scenario: a wired EN input is not folded into the box
- **WHEN** a body wiring a box's EN input is pushed
- **THEN** the enable comes back as an enable
- **AND** it is never folded into the box as an ordinary input, which would change what the program does

#### Scenario: an Execute box survives a create
- **WHEN** a body containing an Execute box (ST inside FBD) is pushed
- **THEN** the box and its ST come back verbatim, or the push is refused naming the Execute box

#### Scenario: network grouping is preserved, or the push is refused
- **WHEN** a body is pushed as one network
- **THEN** it is read back as one network
- **AND** a vendor that regroups by connected component refuses the push rather than silently returning several
  networks, because a body reshaped without a refusal is a difference the engineer cannot see

### Requirement: A vendor difference in the e2e suite is a tracked defect, not a permanent branch

The live-bridge suite SHALL NOT carry a vendor branch for a shape one vendor merely has not implemented. Where a
branch exists, it SHALL assert BOTH sides — the refusal as well as the round trip — so a gap cannot be absorbed
by a test that quietly checks nothing on the vendor that lacks the capability.

#### Scenario: no vendor branch survives in the graphical suite
- **WHEN** the shapes above are supported on both vendors
- **THEN** `grep -rn 'VENDOR === "twincat"' packages/volt-cli/test/e2e/graphical/` returns nothing
- **AND** the full suite is green on both vendors with the same number of passing tests
