## Why

**The live suite is thorough about what it knows, and had no way to say what it had never tried.**

175 e2e tests pass on both vendors. They assert labels, jumps, returns, titles, comments, EN/ENO, fan-out and
Execute boxes — each on CREATE, on the FIXED POINT, and against a real BUILD. That is a high bar, and it still
missed a body a real project holds: `ladderLabel.prg` is two networks, one carrying a coil with nothing driving
it and one carrying nothing but a label. Pushed into an empty TwinCAT project it came back gutted, with the
push reporting success (`twincat-graphical-create-loss`).

Neither shape appears anywhere in `test/e2e`. The suite was not wrong about anything it tested; it had simply
never asked a live IDE to create either one, and nothing could report that.

**`scripts/e2e-graphical-coverage.ts` now can.** It counts every construct the format defines
(`docs/network-text.md` §4/§6/§7) against the e2e sources that actually push it. Measured today: **20 of 25
covered, 5 never pushed at all.**

| gap | why it matters |
|---|---|
| `RESET coil (R=)` | `S=` is pushed three times, `R=` never — and the reset coil is the construct whose misread inverted **128 coils** in one real project. The fix was verified against a corpus, never against a live create. |
| `modifier RISING` | never pushed on either vendor |
| `modifier FALLING` | never pushed — and `AssignOp` was found this session to drop both silently on an assignment target |
| `EMPTY network` | half of what `ladderLabel.prg` lost |
| `undriven coil (x := ;)` | the other half |

## What Changes

- One live e2e test per gap, in the shape the suite already uses: create, pull, assert the construct survived,
  re-push the pulled text, assert the FIXED POINT, and assert the BUILD gained no diagnostic.
- Each is expected to **find something or prove something**. A test that passes first time is a real result;
  three of these five constructs have a history of being mishandled where nothing live exercised them.
- `e2e-graphical-coverage.ts` stays a REPORT, not a CI gate. A construct with no coverage is a question for a
  person, and answering it needs an IDE — a red CI job would only teach people to ignore it.

## Impact

- `packages/volt-cli/test/e2e/graphical/` — the new cases
- `packages/volt-cli/scripts/e2e-graphical-coverage.ts` — the report (already in the tree)
- Any driver fix the new cases turn up
