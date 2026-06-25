# Writes a structured event log for one call.
#
# The tracer records what happened during a call as a series of events: each turn
# taken, who spoke, how long things took, and the timestamps. It saves these
# events to a file so the call can be reviewed and timing can be checked later.
#
# This is a plain logging tool. It does not decide anything about the call.

from typing import Any, Dict, List


class CallTracer:
    """Collects per-call events and saves them to a file.

    The tracer is created at the start of a call. During the call it is told about
    each event as it happens, such as the patient taking a turn or a reply being
    spoken, along with timing. At the end of the call it writes every event to a
    single file, one record per event, for later review.
    """

    def __init__(self, trace_path: str) -> None:
        """Set up a tracer for one call.

        What goes in:
            trace_path: the file path where the event log should be written, for
                example results/traces/<call_id>.jsonl.

        What comes out:
            Nothing. It stores the path and prepares an empty list of events.
        """
        # Steps the real implementation will take:
        # 1. Store trace_path on self.
        # 2. Prepare an empty list to hold events until save is called.
        raise NotImplementedError("CallTracer.__init__ is not implemented yet.")

    def log_turn(self, speaker: str, text: str, latency_seconds: float) -> None:
        """Record one conversational turn and how long it took.

        What goes in:
            speaker: who spoke this turn, either "patient" or "agent".
            text: the words said on this turn.
            latency_seconds: how long it took to produce this turn, measured from
                the end of the other side's speech to the start of this one. This
                is the number that tells us if the agent felt slow.

        What comes out:
            Nothing. The turn is added to the event list with a timestamp.
        """
        # Steps the real implementation will take:
        # 1. Build an event dict with type "turn", the speaker, the text, the
        #    latency, and the current timestamp.
        # 2. Append the event to the in-memory event list.
        raise NotImplementedError("CallTracer.log_turn is not implemented yet.")

    def log_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """Record any other kind of call event that is not a turn.

        Examples are the call connecting, the call ending, or a stop condition
        being reached. Keeping these in the same log gives one ordered story of
        the whole call.

        What goes in:
            event_type: a short label for the kind of event, for example
                "call_started", "call_ended", or "stop_condition".
            details: a dictionary of extra facts about the event. May be empty.

        What comes out:
            Nothing. The event is added to the event list with a timestamp.
        """
        # Steps the real implementation will take:
        # 1. Build an event dict with the given event_type, the details, and the
        #    current timestamp.
        # 2. Append the event to the in-memory event list.
        raise NotImplementedError("CallTracer.log_event is not implemented yet.")

    def save(self) -> str:
        """Write all collected events to the trace file.

        What goes in:
            Nothing.

        What comes out:
            The path to the written trace file, so callers know where the log is.

        Events are written in the order they happened, one record per line, so the
        file reads as a simple timeline of the call.
        """
        # Steps the real implementation will take:
        # 1. Make sure the folder for trace_path exists, creating it if needed.
        # 2. Open trace_path for writing.
        # 3. Write each event as its own line, in the order it was logged.
        # 4. Return trace_path.
        raise NotImplementedError("CallTracer.save is not implemented yet.")

    def events(self) -> List[Dict[str, Any]]:
        """Return the events collected so far, without writing to disk.

        What goes in:
            Nothing.

        What comes out:
            The list of event dictionaries in the order they were logged. This is
            handy for a live view of the call or for tests that check the log.
        """
        # Steps the real implementation will take:
        # 1. Return the in-memory event list.
        raise NotImplementedError("CallTracer.events is not implemented yet.")
