# finding-demo-artifacts

Things we explicitly do NOT count as bugs. These are characteristics of a seeded demo line. They are only "wrong" because the data is placeholder, so they would not be defects in a real deployment. The classifying rule is on [[concept-demo-vs-real]].

## Seeded fake providers and a placeholder address

Bug ID HALL-02, demoted. Asked for a doctor and the office address, the agent named "Dr. Dudy Hauser", "Dr. Adam Bricker", and "Dr. Doug Ross", and gave the address "1234 Recovery Way, Suite 200, Austin".

Evidence:

- Call CA7d1428 [57.3s] AGENT: "Dr. Dudy Hauser and Dr. Adam Bricker both see new and returning patients... Dr. Doug Ross handles more complex cases." and [86.4s] AGENT: "Our office is at 1234 Recovery Way, Suite 200, Austin."
- Confirmation call CAf8e114 [48.6s] returned the same roster and [70.4s] the same address (with minor ASR spelling variants like Judy/Dudy and Brooker/Bricker, covered on [[layer-voice-asr]]).

Two tells that this is seed data: "Dr. Doug Ross" is the lead character of the TV show ER, and "1234 Recovery Way" is a textbook placeholder street address. The deciding tell is consistency. Because the answers are identical across two separate calls, these are fixed seeded placeholders, not on-demand fabrication that would vary call to call. That consistency is what proves it is demo seed data rather than a hallucination bug.

The broader pattern these surfaced (presenting unverifiable specifics confidently) is carried forward as the real bug on [[finding-overconfidence]]. The specific fake doctors and address themselves are a demo characteristic, not a defect. These also belong to [[layer-booking-scope]], since they show up when a caller asks who they could book with.

## Fabricated demo date of birth

The agent invents a demo DOB ("July 4, 2000", described as for demo purposes) rather than soliciting a real one. This is a demo stand-in for a real intake step, not a defect. It is, however, what makes the verification design risk on [[finding-verification-risk]] possible, which is why we flag the design risk while not counting the fabricated DOB itself as a bug.

## Dead "representative" handoff

On a non-emergency dead end the agent offers to "connect you to a representative", and the handoff lands on a "pretty good AI test line" that then says "Goodbye" and disconnects. A demo line has no real front desk to transfer to, so a dead handoff is a demo artifact, not a defect in the agent's logic.

## Why list these at all

Listing what we did NOT count is part of the honesty of the assessment. A less careful tester would have reported the fake doctors, the placeholder address, and the verification path as critical bugs. Separating them out is the whole point of [[concept-demo-vs-real]].

## Related

- [[concept-demo-vs-real]]
- [[layer-booking-scope]]
- [[layer-voice-asr]]
- [[finding-overconfidence]]
- [[finding-verification-risk]]
- [[calls]]
- [[agent-overview]]
