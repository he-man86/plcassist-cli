# Tasks

Run `bun run scripts/e2e-graphical-coverage.ts` before and after: the gap list is the task list, and it is the
thing that says when this is done.

## 1. The two shapes that already cost something

- [ ] An EMPTY network (a marker straight to `END_NETWORK`) round-trips, or is refused by name. Both vendors.
      This is half of `ladderLabel.prg`, and PLCopen has no network element to state it with (D25) — so a named
      refusal is a legitimate outcome and silence is not.
- [ ] An UNDRIVEN coil (`x := ;`) round-trips. It reads back as the TERMINATOR the archive holds rather than a
      null, which `NetworkTextReader` already models — what is untested is creating one.

## 2. The three nothing has ever pushed

- [ ] A RESET coil (`out R= a;`). `S=` is covered three times over; `R=` never, and this is the construct whose
      misread inverted 128 coils in one project. Assert the round trip AND the build.
- [ ] A RISING-edge modifier on a consumed operand.
- [ ] A FALLING-edge modifier on a consumed operand.

## 3. Keep the report honest

- [ ] Re-run the coverage report; every construct is either covered or has a written reason it cannot be.
- [ ] Any construct added to `docs/network-text.md` later appears in the report as a gap until it is pushed —
      confirm by adding a fake row and seeing it listed.
