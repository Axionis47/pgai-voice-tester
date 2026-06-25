# concept-demo-vs-real

The honesty filter principle. This is the single rule we used to classify everything we found, so the report would not inflate demo behavior into bugs.

## The rule

- A real bug is something that is wrong for ANY medical voice agent, demo or not.
- A demo artifact is something that is only "wrong" because this is a seeded demo line with placeholder data. It would not be a defect in a real deployment.

If a behavior fails the first test (wrong regardless of backend), it is a bug. If it only fails because the data behind it is placeholder, it is a demo artifact and we do not count it.

## Why we need it

The target is a DEMO agent, not a live clinic (see [[agent-overview]]). It is seeded with placeholder data that it presents confidently as real: fake doctors, a placeholder address, a fabricated default DOB. A careless tester would log every one of those as a critical bug. Most of them are not bugs at all; they are characteristics of a demo backend.

## How it sorted our findings

- [[finding-overconfidence]] passes the filter as a real bug. Inventing specific practice policy and doubling down is wrong for any medical agent, with or without a demo backend. A patient cannot tell the answer was made up.
- [[finding-verification-risk]] is demoted to a caveated design risk. The verification path is weak, but the only data it exposed was placeholder (a self-fabricated default DOB, no real meds or insurance). With real patient data it would be an account-takeover vector; on the demo line as built it is a risk to flag, not a breach.
- [[finding-demo-artifacts]] fails the filter and is not counted. The fake doctors, placeholder address, fabricated DOB, and dead handoff are all consequences of the demo backend.

## The consistency test

One practical tell sits inside this rule. If a fabricated detail comes back identical across separate calls, it is seeded demo data, not on-demand hallucination. The doctor roster and address were the same across two calls, which is what demoted them to demo artifacts rather than a fabrication bug. A real hallucination would vary call to call.

## Related

- [[finding-overconfidence]]
- [[finding-verification-risk]]
- [[finding-demo-artifacts]]
- [[concept-epistemic-humility]]
- [[agent-overview]]
- [[calls]]
