# Reads the external config files that drive the whole voice tester.
# Nothing in this file decides behavior. It only loads YAML files from disk
# and hands back plain Python dictionaries for the rest of the system to use.

from pathlib import Path
from typing import Any, Dict


def load_settings(settings_path: str) -> Dict[str, Any]:
    """Load the global settings file (infrastructure, voice, turn-taking knobs).

    What goes in:
        settings_path: path to config/settings.yaml as a string.

    What comes out:
        A plain dictionary of every setting, for example API hosts, voice
        choices, and the maximum number of turns per call.

    These settings apply to every call, no matter which scenario is run.
    """
    # Steps the real implementation will take:
    # 1. Turn settings_path into a Path and confirm the file exists.
    # 2. Open the file and parse it with PyYAML safe_load.
    # 3. Return the parsed dictionary, or an empty dict if the file is blank.
    raise NotImplementedError("load_settings is not implemented yet.")


def load_scenario(scenario_path: str) -> Dict[str, Any]:
    """Load one scenario file that describes a single test case.

    What goes in:
        scenario_path: path to a file under config/scenarios/ as a string.

    What comes out:
        A plain dictionary with the scenario fields: id, persona, goal, twist,
        knowledge_pack, steering, expected, severity_if_fails, and voice.

    Each scenario is one test the patient bot will run against the agent.
    """
    # Steps the real implementation will take:
    # 1. Turn scenario_path into a Path and confirm the file exists.
    # 2. Open the file and parse it with PyYAML safe_load.
    # 3. Return the parsed dictionary so the brain can read the scenario fields.
    raise NotImplementedError("load_scenario is not implemented yet.")


def load_knowledge_map(knowledge_map_path: str) -> Dict[str, Any]:
    """Load the living knowledge map of what we know about the target agent.

    What goes in:
        knowledge_map_path: path to config/knowledge_map.yaml as a string.

    What comes out:
        A plain dictionary of accumulated intel about the target agent. This
        grows over time as the offline analysis folds in new findings.

    The brain reads this map to steer the patient toward known weak spots.
    """
    # Steps the real implementation will take:
    # 1. Turn knowledge_map_path into a Path and confirm the file exists.
    # 2. Open the file and parse it with PyYAML safe_load.
    # 3. If the file is missing or empty, return an empty dict so a first run
    #    still works before any intel has been gathered.
    raise NotImplementedError("load_knowledge_map is not implemented yet.")
