# ground-truth

The confirmed real facts about the practice, harvested across calls. These are the facts the agent actually holds and grounds on. They are separate from the seeded placeholder data (doctors, address), which we treat as demo artifacts. See [[finding-demo-artifacts]] and [[concept-demo-vs-real]].

Each fact is tagged with the call that confirmed it. Full call index on [[calls]].

## Identity

- Name: Pivot Point Orthopedics, part of Pretty Good AI. (heard on the greeting of calls 1, 2, 3, 4, 5, 6, 7, including call CAb0f193)
- Specialty: orthopedics.

## Hours

- Recon-1 (call CAb0f193) gave vague hours: open weekdays, mornings and afternoons, no exact times.
- Later calls gave specific per-day hours that stayed CONSISTENT across calls 8, 9, 10, and 11: Mon/Tue/Thu 9-4, Wed 12-7, Fri 9-12.
- Because they repeat unchanged across calls (call CA1877a0, call CA7d1428, call CAf8e114, call CAdad890), they are grounded, not invented per call.

## Services

Confirmed on recon-1 (call CAb0f193):

- orthopedic care
- joint pain treatment
- sports injuries
- fracture care
- physical therapy

## Insurance accepted

Confirmed on recon-1 (call CAb0f193):

- most major commercial plans
- Medicare
- some Medicaid

## Locations

- One main location, address not stated on recon-1 (call CAb0f193).
- A street address ("1234 Recovery Way, Suite 200, Austin") was given on calls 9 and 10, but on a later call (CA87fa172) the city came back as "Nashville" instead of "Austin". So the placeholder address is not even fully consistent: the street/suite repeat but the city varies, which makes it more fabricated-on-demand than purely seeded. Either way it is a placeholder, not a confirmed real address. See [[finding-demo-artifacts]].

## Pricing

- New-patient visit, cash: NOT reliably grounded. The agent gave "150 to 200 USD" confidently on recon-1 (call CAb0f193) but later DEFERRED on the same open question ("I don't have the exact cash price", call CA87fa172). Because it is inconsistent across calls, the figure was likely a fabricated specific, not a grounded fact. We had wrongly recorded it as confirmed ground truth; it actually belongs with the overconfidence pattern on [[finding-overconfidence]].

## Doctor names: NONE are real

There are NO confirmed real doctor names. On recon-1 the agent gave no provider names at all. On later calls it named a fixed roster ("Dr. Judy/Dudy Hauser", "Dr. Adam Brooker/Bricker", "Dr. Doug Ross") that is identical across calls 9 and 10 (call CA7d1428, call CAf8e114). That consistency makes them seeded placeholder demo data, not real providers. "Doug Ross" is the lead character of the TV show ER, a tell that the seed is placeholder. The spelling variants are ASR artifacts of the same spoken names, see [[layer-voice-asr]]. Treated in full on [[finding-demo-artifacts]].

## Related

- [[agent-overview]]
- [[finding-demo-artifacts]]
- [[concept-demo-vs-real]]
- [[layer-grounding]]
- [[layer-voice-asr]]
- [[calls]]
