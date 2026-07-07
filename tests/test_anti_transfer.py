# Regression tests pinning down the patient's universal call behavior.
#
# The patient in a test call is played by one Gemini Live session, and how it
# behaves comes entirely from the system instruction that src/brain.py builds from
# the scenario. The target receptionist agent has one failure that ends calls too
# soon: when it gets stuck or caught in a loop, most often the identity-verification
# loop, it hands the call to a dead-end line that just says goodbye. That hand-off
# connects to nothing useful and cannot be refused or salvaged, so the only fix is
# to keep the agent from ever getting stuck.
#
# Two behaviors keep it moving. First, the phone number the patient calls from is on
# file for a patient the agent knows as John, so the patient answers to John and
# lets the agent look up the record by that number, which makes verification succeed
# at once. Second, the patient cooperates promptly and in full with whatever the
# agent asks, so the agent never has to ask twice. On top of that, the patient never
# ends the call while it still has an open request or an unaddressed health concern.
#
# build_system_instruction adds this behavior universally, not gated on any scenario
# field. These tests pin it down for a bare-bones scenario with no special fields,
# since it is meant to apply everywhere. They use the standard-library unittest
# module and build a minimal scenario dictionary by hand, so no config file, live
# call, or network is needed.

import os
import sys
import unittest

# Make the repo root importable so "from src.brain import ..." resolves no matter
# how the tests are launched. This file lives in tests/, so the repo root is two
# levels up.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.brain import build_system_instruction


def make_minimal_scenario():
    """Build the smallest scenario dictionary these tests need.

    What goes in:
        Nothing.

    What comes out:
        A plain scenario dictionary with only a persona and a goal, and none of the
        optional fields like opening_line, twist, or steering. The call behavior is
        universal, so it must appear even for a scenario this bare. A minimal
        scenario is the strongest way to prove the behavior is not gated on any
        special field.
    """
    return {
        "persona": "A calm adult patient named Maria who speaks plainly.",
        "goal": "Sort out a prescription refill and a follow-up appointment.",
    }


class JohnIdentityTests(unittest.TestCase):
    """Pin down that every patient is told to be John for the number on file."""

    def test_instruction_tells_the_patient_to_confirm_the_john_identity(self):
        """The built instruction must tell the patient to answer to John.

        The phone number the patient calls from is registered to a patient the
        agent knows as John, and the agent greets callers as John. Confirming John
        makes the lookup succeed instantly; claiming a different name mismatches the
        record and loops the agent into a dead-end transfer. This checks the
        instruction names John and tells the patient to confirm that identity. If
        this text goes missing, the patient may give a different name and get stuck.
        """
        instruction = build_system_instruction(make_minimal_scenario(), {})

        self.assertIn(
            "Your name on this call is John",
            instruction,
            "the instruction must tell the patient its name on this call is John so "
            "the lookup on the number on file succeeds",
        )
        self.assertIn(
            "registered to a patient named John",
            instruction,
            "the instruction must explain the calling number is registered to John "
            "so the patient understands why to confirm that name",
        )
        self.assertIn(
            "confirm that it is",
            instruction,
            "the instruction must tell the patient to confirm it when the agent asks "
            "whether it is speaking with John",
        )


class CooperationTests(unittest.TestCase):
    """Pin down that every patient is told to cooperate promptly so it never sticks."""

    def test_instruction_tells_the_patient_to_cooperate_promptly(self):
        """The built instruction must tell the patient to answer requests in full.

        The agent hands stuck calls to a dead-end line, so the patient must give
        whatever the agent asks for promptly and in full the first time and never
        make it ask twice. This checks the instruction carries that cooperation
        direction and names the dead-end hand-off it is meant to avoid. If this text
        goes missing, the patient may stall and trigger the transfer.
        """
        instruction = build_system_instruction(make_minimal_scenario(), {})

        self.assertIn(
            "Be an easy, cooperative caller",
            instruction,
            "the instruction must tell the patient to be an easy, cooperative caller "
            "so the agent never gets stuck",
        )
        self.assertIn(
            "in full the first time",
            instruction,
            "the instruction must tell the patient to give what the agent asks for "
            "in full the first time so it does not have to ask twice",
        )
        self.assertIn(
            "dead-end line",
            instruction,
            "the instruction must name the dead-end line the agent hands stuck calls "
            "to, so the patient knows what it is avoiding",
        )


class DoNotEndEarlyTests(unittest.TestCase):
    """Pin down that every patient is told not to end the call too early."""

    def test_instruction_tells_the_patient_not_to_end_early(self):
        """The built instruction must tell the patient not to end the call.

        The patient must never be the one who ends the call: it must not say
        goodbye, hang up, or start wrapping up while it still has an open request or
        an unaddressed health concern. This checks the instruction carries that
        do-not-end-early direction so the call runs long enough to test the agent.
        """
        instruction = build_system_instruction(make_minimal_scenario(), {})

        self.assertIn(
            "Never be the one who ends the call",
            instruction,
            "the instruction must tell the patient never to be the one who ends the "
            "call while a request or health concern is still open",
        )
        self.assertIn(
            "gently steer back to what you still need",
            instruction,
            "the instruction must tell the patient to keep talking and steer back "
            "to its goal if the agent tries to close the call",
        )


if __name__ == "__main__":
    unittest.main()
