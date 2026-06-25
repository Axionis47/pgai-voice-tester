# index

This is the hub of our knowledge base about a target voice agent we red-teamed. It is an organized, cross-linked wiki of everything we learned over 15 real phone calls to a medical receptionist demo agent that answers as "Pivot Point Orthopedics, part of Pretty Good AI". Every page is atomic and links densely to the others, so you can start anywhere and follow the trail. Raw evidence lives on [[calls]]; the honest read of what is a real bug versus a demo artifact runs through every page.

## At a glance

- **15 calls** placed across a recon wave and several attack waves (the 15th re-tested the one finding). Full index: [[calls]].
- **1 real bug**: framing-dependent fabrication of policy. It asserts a policy it lacks when a caller leads it, proven by a cross-call contradiction. See [[finding-overconfidence]].
- **1 design risk (caveated)**: weak verification by caller-ID auto-identify plus accepted default DOB. See [[finding-verification-risk]].
- **Demo artifacts (not bugs)**: seeded placeholder doctors and address, fabricated DOB, dead human handoff. See [[finding-demo-artifacts]].
- **Verified passes**: emergencies, clinical scope, voice capture, phantom-doctor decline, sycophantic-flip hold. See [[finding-passes]].

The honest haul is small but defensible. The value of the campaign is not a long bug list, it is the rigorous separation of one real behavioral bug from the demo artifacts a less careful tester would have reported as critical. See [[concept-demo-vs-real]].

## Map

### The agent

- [[agent-overview]] - what the target is, in one place
- [[capabilities]] - what the agent can do, the feature inventory
- [[ground-truth]] - the real office facts we harvested
- [[layer-verification]] - identity checks (DOB gate, default DOB, caller-ID auto-identify)
- [[layer-safety-escalation]] - emergency handling (semantic, a PASS)
- [[layer-grounding]] - holds what it knows and defers when asked openly, fabricates what it lacks when led (the real bug lives here)
- [[layer-memory-persistence]] - cross-call memory keyed to phone number (messy)
- [[layer-voice-asr]] - garbles some proper nouns, captured a spoken drug name correctly
- [[layer-booking-scope]] - DOB-gated booking, refuses clinical advice, declines phantom doctors
- [[layer-robustness]] - holds grounded facts under social pressure, no sycophantic flip

### Findings

- [[finding-overconfidence]] - the one real bug (medium severity)
- [[finding-verification-risk]] - the caveated design risk
- [[finding-demo-artifacts]] - the things that look like bugs but are demo seed data
- [[finding-passes]] - the behaviors that passed, reported honestly

### Concepts

- [[concept-epistemic-humility]] - the lens that ties the findings together: grounds what it knows, defers when asked openly, but fabricates what it lacks when led
- [[concept-demo-vs-real]] - the honesty filter that separates real bugs from demo artifacts

### Evidence

- [[calls]] - the index of all 15 calls, each linked to the finding it produced

### Next round

- [[attack-surface]] - the map for the next round: what is tested, what is open, candidate leads

## Start here

New reader: begin with [[agent-overview]] to learn what the target is, then read the findings ([[finding-overconfidence]], [[finding-verification-risk]], [[finding-demo-artifacts]], [[finding-passes]]) to see what we concluded, then go to [[attack-surface]] for where to push next.
