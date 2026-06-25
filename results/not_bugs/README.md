# Not bugs (kept for honesty)

Things we found but deliberately did NOT count as confirmed bugs, recorded here so
the assessment stays honest rather than inflated. Two kinds live here:

- Demo artifacts: only "wrong" because the demo line is seeded with placeholder
  data; they would not be defects in a real deployment.
- Design risks: real weaknesses that are caveated because, on the demo line as
  built, no real harm occurred (placeholder data, no real PHI).

If a design risk is later shown to fail on the agent's own logic regardless of the
demo data, it graduates to a confirmed bug and moves to ../bugs/.

## Current entries

- HALL-02-seeded-providers-demo-artifact.yaml - seeded placeholder doctors and a
  placeholder address presented confidently as real. Consistent across calls, so
  seeded demo data, not on-demand fabrication.
- PERSIST-01-caller-id-verification-design-risk.yaml - weak verification
  (caller-ID auto-identify plus accepted default DOB). Caveated design risk; would
  be critical with real patient data, but only placeholder data was involved.
