# concept-epistemic-humility

The cross-cutting idea behind the one real bug. Epistemic humility is an agent knowing the edges of what it knows: saying "I am not sure" or "let me confirm that" when it lacks the fact, instead of filling the gap with a confident guess.

## The observation

Across all 14 calls the target never expressed uncertainty. It never said "I do not know", "I cannot confirm that", or "let me check with the office". It commits to an answer every time. When it has the fact, that confidence is correct. When it lacks the fact, that same confidence becomes fabrication.

## The sharp split

This concept is what makes the central finding precise. The agent does two opposite things depending on whether it holds the fact:

- Holds what it knows. It rejected a false Saturday-hours premise, held its real Friday hours under pressure (call CAdad890), and gave the same per-day hours across four calls. These are on [[finding-passes]].
- Fabricates what it lacks. It invented a no-cancellation-fee and no-referral policy and doubled down on confirm (call CA4eec72). This is the real bug on [[finding-overconfidence]].

The difference between the two is not honesty versus dishonesty. It is the total absence of a "low-confidence" mode. The agent has no behavior for "I am not sure", so when grounding runs out, confident assertion is the only thing left.

## Why this framing matters

"The agent hallucinates" is too blunt; it does not hallucinate the things it has grounded. "The agent lacks epistemic humility" is sharper and survives the honesty filter, because the fix is specific: give the agent a deferral path for ungrounded policy. This concept ties [[finding-overconfidence]] together and lives in [[layer-grounding]].

## The lens for the next round

Epistemic humility is the lens we carry into future probes on [[attack-surface]]. The open untested vector, under-triage by framing (a real emergency disguised as a routine question), is the same failure mode in a more dangerous place: the agent committing to a confident answer in a situation where it should hesitate.

## Related

- [[finding-overconfidence]]
- [[layer-grounding]]
- [[finding-passes]]
- [[attack-surface]]
- [[agent-overview]]
