# Regression tests pinning down the scenario opening_line behavior.
#
# The patient in a test call is played by one Gemini Live session, and how it
# behaves comes entirely from the system instruction that src/brain.py builds from
# the scenario. In a real call the patient improvised its first turn and collapsed
# the whole scenario into a wrap-up line, skipping the scripted requests and a
# critical health symptom it was supposed to say. To stop that, a scenario may set
# an optional opening_line: the exact thing the patient must say as its first turn.
#
# These tests pin down two facts about build_system_instruction:
#
#   1. When a scenario has a non-empty opening_line, the built instruction must
#      contain that line's text AND a mandatory, first-turn directive telling the
#      patient to say it first and in full. If either goes missing, the patient is
#      free to improvise the opening again.
#
#   2. When a scenario has no opening_line, the built instruction must be exactly
#      what it was before this feature: no opening-line text, no first-turn
#      directive. This guards scenarios that intentionally let the patient open the
#      call naturally on its own.
#
# The tests use the standard-library unittest module and build a minimal scenario
# dictionary by hand, so no config file, live call, or network is needed.

import os
import sys
import unittest

# Make the repo root importable so "from src.brain import ..." resolves no matter
# how the tests are launched. This file lives in tests/, so the repo root is two
# levels up.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.brain import build_system_instruction


# A short opening line that carries a critical health symptom, so the tests can
# check the symptom text survives into the instruction and is not summarized away.
OPENING_LINE_TEXT = (
    "Hi, I need to refill my blood pressure medication and book a follow-up, "
    "and I have also been having chest pain for the last two days."
)


def make_scenario(include_opening_line):
    """Build a minimal scenario dictionary for these tests.

    What goes in:
        include_opening_line: when True the scenario carries a non-empty
            opening_line; when False the opening_line key is left out entirely, so
            the two scenarios are identical apart from that one field.

    What comes out:
        A plain scenario dictionary with a persona and a goal, plus the
        opening_line only when asked for. Keeping the rest of the scenario fixed
        lets a test compare the with and without cases directly.
    """
    scenario = {
        "persona": "A calm adult patient named Maria who speaks plainly.",
        "goal": "Sort out a prescription refill and a follow-up appointment.",
    }
    if include_opening_line:
        scenario["opening_line"] = OPENING_LINE_TEXT
    return scenario


class OpeningLinePresentTests(unittest.TestCase):
    """Pin down what must appear when a scenario sets an opening_line."""

    def test_instruction_includes_the_opening_line_text(self):
        """The built instruction must carry the opening line's exact text.

        The whole point of opening_line is that the patient says a specific,
        complete line. If the text does not reach the system instruction, the model
        never sees what it is supposed to say. This checks the full line and, on its
        own, the critical health symptom, so a future change that truncates the line
        would fail here.
        """
        instruction = build_system_instruction(make_scenario(True), {})

        self.assertIn(
            OPENING_LINE_TEXT,
            instruction,
            "the opening line text must appear verbatim in the system instruction "
            "so the patient sees exactly what to say",
        )
        self.assertIn(
            "chest pain",
            instruction,
            "the critical health symptom in the opening line must survive into the "
            "instruction and not be summarized away",
        )

    def test_instruction_includes_a_mandatory_first_turn_directive(self):
        """The built instruction must tell the patient this is a mandatory first turn.

        The text alone is not enough; without a directive the model may fold the
        line into a later turn or skip parts of it. This checks the instruction
        marks the line as mandatory and as the first thing the patient says.
        """
        instruction = build_system_instruction(make_scenario(True), {})

        self.assertIn(
            "MANDATORY",
            instruction,
            "the opening-line section must be marked mandatory so the model cannot "
            "treat it as optional",
        )
        self.assertIn(
            "FIRST TURN",
            instruction,
            "the directive must tell the patient to say the opening line on its "
            "first turn",
        )


class OpeningLineAbsentTests(unittest.TestCase):
    """Pin down that no opening_line means no new text at all."""

    def test_no_opening_line_adds_no_directive_or_text(self):
        """Without an opening_line the instruction must gain no opening-line content.

        Scenarios that leave opening_line out expect the patient to open the call on
        its own. This checks the built instruction contains neither the opening-line
        text nor the mandatory first-turn directive when the field is absent.
        """
        instruction = build_system_instruction(make_scenario(False), {})

        self.assertNotIn(
            OPENING_LINE_TEXT,
            instruction,
            "no opening_line was set, so its text must not appear in the "
            "instruction",
        )
        self.assertNotIn(
            "YOUR FIRST TURN (MANDATORY, SAY THIS FIRST):",
            instruction,
            "no opening_line was set, so the first-turn directive must not be "
            "added",
        )

    def test_absent_matches_the_pre_feature_instruction(self):
        """Dropping opening_line must leave the rest of the instruction unchanged.

        Adding the field must not disturb the sections that were already there. This
        builds the same scenario with and without the opening_line and checks that
        removing the field gives back exactly the sections built from the shared
        persona and goal, with none of the opening-line block spliced in.
        """
        with_opening = build_system_instruction(make_scenario(True), {})
        without_opening = build_system_instruction(make_scenario(False), {})

        # The two instructions share the same persona and goal sections. The only
        # difference must be the opening-line block, so the without-opening version
        # is a strict prefix-free subset: it must not contain the opening block, and
        # it must still contain the persona the two scenarios share.
        self.assertIn(
            "WHO YOU ARE:",
            without_opening,
            "the persona section must still be present when opening_line is absent",
        )
        self.assertNotIn(
            "YOUR FIRST TURN (MANDATORY, SAY THIS FIRST):",
            without_opening,
            "the opening-line block must be the only thing the field adds",
        )
        self.assertNotEqual(
            with_opening,
            without_opening,
            "setting opening_line must actually change the instruction, otherwise "
            "the feature does nothing",
        )


if __name__ == "__main__":
    unittest.main()
