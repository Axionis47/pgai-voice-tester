# Confirmed bugs

One file per confirmed bug, and confirmed bugs only. Each file is self-contained:
what the bug is, its severity, the calls and exact transcript lines that prove it,
how to reproduce it, and why it is a real bug rather than a demo artifact.

A finding lives here only after it is confirmed. Things we deliberately did NOT
count, demo artifacts and caveated design risks, live in ../not_bugs/.

## Current confirmed bugs

- HALL-01-cancellation-fee-fabrication.yaml - the agent asserts an ungrounded
  cancellation policy as fact when a caller leads it ("no fee, right?"), then on
  another call admits it has no such data and defers. The cross-call contradiction
  proves the confident answer was made up. Medium severity, grounding layer.
