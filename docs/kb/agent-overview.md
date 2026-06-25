# agent-overview

What the target is, in one place. This is the entry point for the agent-specific pages. For the wiki landing page see [[index]].

## Identity

The target is a medical receptionist voice agent that answers as "Pivot Point Orthopedics, part of Pretty Good AI". It is an orthopedics practice front desk. It books appointments, runs refill intake, and answers general office questions over the phone.

It is a DEMO agent, not a live clinic line. This matters for every finding. Some of what it says is seeded placeholder data presented confidently as real, and some of its dead ends (like the human handoff) are demo stand-ins. We separate those demo artifacts from real bugs everywhere in this wiki. See [[concept-demo-vs-real]] and [[finding-demo-artifacts]].

We tested it over 14 real phone calls (a recon wave plus several attack waves). The full call index with callSids is on [[calls]]. For the positive inventory of what it can actually do (its features, with the calls that demonstrated each), see [[capabilities]].

## One-line verdict

It is genuinely well built. After an honesty filter the haul is small: 1 real bug, 1 caveated design risk, and several demo artifacts that are not bugs. See [[finding-overconfidence]] for the one real bug.

## The 7 behavior layers

We mapped the agent across these layers. Each has its own page.

- [[layer-verification]] - how it checks identity (DOB gate, accepts a default DOB, auto-identifies by caller ID)
- [[layer-safety-escalation]] - emergency handling (semantic and correct, a PASS)
- [[layer-grounding]] - holds facts it knows, fabricates specifics it lacks (the real bug lives here)
- [[layer-memory-persistence]] - cross-call memory keyed to phone number (messy, unreliable)
- [[layer-voice-asr]] - garbles some proper nouns, captured a spoken drug name correctly
- [[layer-booking-scope]] - gates booking on DOB, refuses clinical advice, declines phantom doctors
- [[layer-robustness]] - holds grounded facts under social pressure, no sycophantic flip

## Ground truth

The real office facts we harvested (services, insurance, hours, cash price) are on [[ground-truth]], each tagged to the call that confirmed it.

## Related

- [[index]]
- [[capabilities]]
- [[ground-truth]]
- [[layer-verification]]
- [[layer-safety-escalation]]
- [[layer-grounding]]
- [[layer-memory-persistence]]
- [[layer-voice-asr]]
- [[layer-booking-scope]]
- [[layer-robustness]]
- [[finding-overconfidence]]
