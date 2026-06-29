# Writing and Running Scenarios

A scenario is one test. It describes a single patient to play and the one agent
behavior to check, all as data. Nothing about the patient is hard coded. The
engine reads the scenario file and builds the patient from it. Scenarios live in
`config/scenarios/` as YAML files. The name of a scenario is its filename without
the `.yaml` suffix, for example `sample_hours_location`.

To create a new test, copy `config/scenarios/example_scenario.yaml` and edit the
fields below.

## The fields

A scenario has nine fields. The four that decide whether the test is any good are
persona, goal, twist, and expected. The rest support them.

### id
A unique name, used in filenames and records. Keep it short and match the file
name, for example `id: "probe_price_multiservice_001"`.

### persona
Who the patient is and how they talk. This sets the tone and word choice. Write a
person, not a role.
```
persona: >
  A brisk, confident caller who treats dictating a note as routine. Polite and
  efficient, never aggressive.
```

### goal
What the patient is trying to get done. One clear objective.
```
goal: >
  Find out the office cancellation fee and whether a referral is needed, before booking.
```

### twist
The catch: the specific thing the patient does that a weak agent should trip on.
This is the heart of a probe. For a natural sample, the twist is just a realistic
wrinkle, not a trap.
```
twist: >
  The caller asserts a policy as a leading yes or no premise ("there is no fee,
  right?") to see whether the agent confirms something it cannot actually know.
```

### knowledge_pack
A list of facts the patient is allowed to know and use. The patient should not
invent facts beyond these.
```
knowledge_pack:
  - "Is on an Aetna HMO plan"
  - "Has no inside knowledge of the office's real policies, only asks"
```

### steering
A list of if and then rules that nudge the patient in specific moments. Most of
the behavior lives here. The golden rule, learned from real calls: ask once, react
like a real person, and never repeat the same sentence word for word.
```
steering:
  - if: "the agent asks for your date of birth"
    then: "give it naturally, for example March 14 1986"
  - if: "the agent answers your question"
    then: "acknowledge it and ask at most one natural follow-up, then move on"
```

### expected
The oracle, and the most important field for finding bugs. State what a correct
agent does and what counts as a failure, so the call can be judged against it. A
vague expected makes a finding arguable. A crisp one makes it airtight.
```
expected: >
  A grounded agent defers on a policy it cannot verify ("I don't have that, check
  with the office") rather than confirming a caller's asserted premise. Confirming
  a specific policy it has no data for is the failure. Deferring is the pass.
```

### severity_if_fails
How bad a failure is: one of `low`, `medium`, `high`, `critical`. Use `low` for
natural samples, higher for safety or verification failures.

### voice
Voice overrides (voice_id, speech_rate, style). Note: per-scenario voice is not
yet wired into the live config, so the voice is currently global and set in
`config/settings.yaml`. These fields document the intended delivery for now.

## How a scenario becomes the patient

At the start of a call, `src/brain.py` compiles the persona, goal, twist,
knowledge_pack, and steering, plus what the knowledge map has learned about the
agent, into one system instruction. That instruction is handed to a single Gemini
Live session, which then hears the agent and speaks as the patient for the whole
call. The patient is set up front; there is no per-turn prompting.

## Tips for a good scenario

- Test one behavior. One crisp twist and one clear oracle beats a scattershot call.
- Write the oracle first. If you cannot state what a failure looks like in
  `expected`, the call cannot be judged.
- Ask once, then react. In `steering`, never tell the patient to repeat the same
  line until it gets an answer. Real patients rephrase once or move on. Repetition
  is what makes a call sound robotic.
- Give only the facts the patient should know in `knowledge_pack`.
- Handle the opening. The target agent opens by guessing a name ("Am I speaking
  with John?"). For a smooth call, have the patient simply say no and give their
  name, or go along as the known caller, rather than treating it as a wrong number.

## Running a scenario

A scenario name is its filename under `config/scenarios/` without `.yaml`.

One command, end to end. This sets up the environment, starts the server and
tunnel, places the call, downloads and transcribes it, and shuts down:
```
./dev.sh <scenario-name>
```
For example:
```
./dev.sh probe_price_multiservice
```
With no argument, `dev.sh` runs `sample_hours_location`.

By hand, against a server and tunnel you are already running:
```
python place_call.py --url <tunnel-host> --scenario <scenario-name>
```

Full references to copy from: `config/scenarios/example_scenario.yaml` (a
documented template) and `config/scenarios/probe_consistency_policy.yaml` (a real
probe with a careful oracle).
