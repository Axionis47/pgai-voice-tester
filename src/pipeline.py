# This file orchestrates one call.
#
# Under the Gemini Live design the audio streams continuously: a single live
# session hears the agent and speaks as the patient on its own. This file does not
# run a hear -> think -> speak loop itself. Instead it starts telephony and the
# live session, wires the agent's audio into the session and the session's audio
# back to the call, and then watches the call until a clear stop condition is met.
#
# We still reason in turns. Even though audio is continuous, the pipeline tracks
# turn boundaries so it can log each turn, apply mid call steering, and check stop
# conditions. It also drives the recorder and the tracer along the way.

from typing import Optional
from dataclasses import dataclass
from enum import Enum


class StopReason(Enum):
    """
    The set of reasons one call can end.

    Each value names one clear stop condition so callers can log it and
    decide what to do next. The call always ends with exactly one of these.
    """

    # The patient's goal for the scenario was reached.
    GOAL_REACHED = "goal_reached"

    # The conversation got stuck and cannot move forward (a dead end).
    DEAD_END = "dead_end"

    # We hit the maximum number of turns allowed for one call.
    MAX_TURNS = "max_turns"

    # The agent on the other end hung up the call.
    AGENT_HUNG_UP = "agent_hung_up"

    # Something went wrong (audio drop, service error, and so on).
    ERROR = "error"


@dataclass
class PipelineResult:
    """
    The summary of one finished call.

    Fields:
        stop_reason: Which stop condition ended the call.
        turns_completed: How many patient turns happened before the call ended.
        goal_reached: True only when the patient achieved the scenario goal.
        error_message: A short note when stop_reason is ERROR, otherwise None.
    """

    stop_reason: StopReason
    turns_completed: int
    goal_reached: bool
    error_message: Optional[str] = None


class Pipeline:
    """
    Orchestrates one call end to end.

    It does not own any telephony, model, or file logic itself. It only drives
    the pieces handed to it: the call session (carries audio to and from the
    live session), the brain (holds the single Gemini Live session that hears
    the agent and speaks as the patient, and supplies mid call steering), the
    recorder (saves the call audio), and the tracer (logs each turn and timing).

    Because the live session streams audio on its own, the pipeline's role is to
    start everything, bridge the audio, and then supervise: watch turn boundaries
    to log turns, push steering when a rule fires, and end the call on the first
    stop condition.
    """

    def __init__(
        self,
        call_session: object,
        brain: object,
        recorder: object,
        tracer: object,
        max_turns: int,
    ) -> None:
        """
        Store the pieces the call needs and the turn limit.

        Inputs:
            call_session: The live phone call. Carries the agent's audio into the
                Gemini Live session and the patient's audio from the session back
                out to the agent.
            brain: Holds the single Gemini Live session that hears the agent and
                speaks as the patient. Also supplies mid call steering when a
                scenario rule fires.
            recorder: Saves the call audio for later transcription.
            tracer: Logs each turn, who spoke, and the timing of each turn.
            max_turns: The hard cap on how many patient turns the call may run.
                This guarantees the call always ends even if nothing else stops it.

        Output:
            None. The object is ready to run after construction.
        """

        self.call_session = call_session
        self.brain = brain
        self.recorder = recorder
        self.tracer = tracer
        self.max_turns = max_turns

    async def run(self) -> PipelineResult:
        """
        Run one call until a stop condition is met.

        The pipeline starts the live session and the phone call, bridges audio
        between them, and then supervises the streaming conversation. Audio flows
        continuously through the live session, but the pipeline still observes
        turn boundaries so it can log, steer, and check for stop conditions.

        On each turn boundary the pipeline:
            1. Logs the turn and its timing with the tracer.
            2. Checks the scenario's steering rules and, if one fires, pushes the
               steering instruction into the live session through the brain.
            3. Checks whether the goal is reached or the conversation has dead
               ended, and whether the turn limit has been hit.

        The call stops on the first of these conditions:
            - GOAL_REACHED: the scenario goal is satisfied.
            - DEAD_END: the conversation cannot progress.
            - MAX_TURNS: the patient turn count reaches max_turns.
            - AGENT_HUNG_UP: the call session reports the agent ended the call.
            - ERROR: any step raises an unexpected failure.

        Input:
            None. Uses the pieces stored at construction time.

        Output:
            A PipelineResult describing why the call ended and how far it got.
        """

        # Steps the real version will take:
        # 1. Start the brain's Gemini Live session so it is ready to hear and speak.
        # 2. Wire the call session's incoming agent audio into the live session,
        #    and wire the live session's patient audio back into the call session.
        # 3. Register a call-ended handler so an agent hang up stops the call.
        # 4. Place the call and let audio stream continuously.
        # 5. Start a patient turn counter at zero.
        # 6. As each turn boundary is observed, log the turn with the tracer and
        #    hand the turn's audio to the recorder.
        # 7. On each boundary, run the brain's steering check and, if a rule fires,
        #    push the steering instruction into the live session.
        # 8. On each boundary, check for goal reached or dead end and stop if so.
        # 9. Increase the turn counter; if it reaches max_turns, stop with MAX_TURNS.
        # 10. If the call-ended handler fires first, stop with AGENT_HUNG_UP.
        # 11. Wrap any unexpected failure as an ERROR result.
        raise NotImplementedError("Pipeline.run is not implemented yet.")
