# This file is the entry point for one test run.
# You give it a scenario, and it carries that scenario from start to finish.
#
# Start to end flow:
#   1. Parse the --scenario argument from the command line.
#   2. Load the global settings and the chosen scenario spec from config.
#   3. Place the phone call to the medical receptionist agent.
#   4. Run the live round loop (the pipeline) until a stop condition.
#   5. Save the call recording and the turn trace to disk.
#   6. Run the offline path: transcribe the audio, analyze actual vs expected
#      behavior into a bug record, and fold findings into the knowledge map.
#
# The live path produces raw call artifacts. The offline path turns those
# artifacts into findings that shape the next call.

import argparse
from typing import Any, Dict


def parse_arguments() -> argparse.Namespace:
    """
    Read the command line arguments for one run.

    Input:
        None. Reads directly from the process command line.

    Output:
        A namespace with a scenario field holding the scenario id or path
        passed via --scenario.
    """

    # Steps the real version will take:
    # 1. Build an argument parser with a short description.
    # 2. Add a required --scenario argument naming which scenario to run.
    # 3. Parse and return the arguments.
    raise NotImplementedError("parse_arguments is not implemented yet.")


def load_run_config(scenario_name: str) -> Dict[str, Any]:
    """
    Load settings and the scenario spec for this run.

    Input:
        scenario_name: The scenario id or file name chosen on the command line.

    Output:
        A dictionary holding the merged settings and the loaded scenario spec,
        ready to drive the call.
    """

    # Steps the real version will take:
    # 1. Read the global settings file from config.
    # 2. Read the matching scenario spec from config/scenarios.
    # 3. Combine them into one config dictionary and return it.
    raise NotImplementedError("load_run_config is not implemented yet.")


def run_live_call(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Place the call and run the live round loop.

    Input:
        config: The merged settings and scenario spec for this run.

    Output:
        A dictionary of call artifacts, including where the recording and the
        trace were stored and why the loop stopped.
    """

    # Steps the real version will take:
    # 1. Build the brain, recorder, and tracer from the config.
    # 2. Place the phone call and open the audio stream.
    # 3. Build the pipeline with these pieces and the max turn limit.
    # 4. Run the pipeline and capture its result.
    # 5. Return the recording path, trace path, and stop reason.
    raise NotImplementedError("run_live_call is not implemented yet.")


def run_offline_analysis(config: Dict[str, Any], call_artifacts: Dict[str, Any]) -> None:
    """
    Turn the raw call artifacts into findings.

    Input:
        config: The merged settings and scenario spec for this run.
        call_artifacts: Paths and details produced by the live call.

    Output:
        None. The findings and the updated knowledge map are written to disk.
    """

    # Steps the real version will take:
    # 1. Transcribe the saved recording into a clean transcript.
    # 2. Analyze the transcript against the scenario's expected behavior.
    # 3. Write a bug record with a severity when behavior does not match.
    # 4. Fold the findings into the living knowledge map for the next call.
    raise NotImplementedError("run_offline_analysis is not implemented yet.")


def main() -> None:
    """
    Run one full test from command line to written findings.

    Input:
        None. Driven by command line arguments.

    Output:
        None. Side effects are the saved recording, trace, bug record, and the
        updated knowledge map.
    """

    # Steps the real version will take:
    # 1. Parse the command line arguments.
    # 2. Load the run config for the chosen scenario.
    # 3. Run the live call and collect its artifacts.
    # 4. Run the offline analysis over those artifacts.
    raise NotImplementedError("main is not implemented yet.")


if __name__ == "__main__":
    main()
