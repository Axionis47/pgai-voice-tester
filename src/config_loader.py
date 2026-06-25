# Reads the external config files that drive the whole voice tester.
# Nothing in this file decides behavior. It only loads YAML files from disk
# and hands back plain Python dictionaries for the rest of the system to use.

from pathlib import Path
from typing import Any, Dict

import yaml


# Canonical locations of the project's config files, resolved relative to this
# file so they work no matter which directory the program is started from. This
# is the one place that knows where config lives, so paths are never repeated.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SETTINGS_PATH = PROJECT_ROOT / "config" / "settings.yaml"
KNOWLEDGE_MAP_PATH = PROJECT_ROOT / "config" / "knowledge_map.yaml"
SCENARIOS_DIR = PROJECT_ROOT / "config" / "scenarios"


def _read_yaml_file(path: Path) -> Dict[str, Any]:
    """Read one YAML file from disk and return it as a dictionary.

    What goes in:
        path: the path to a YAML file, as a string or a Path.

    What comes out:
        The parsed contents as a dictionary. A missing file or an empty file
        gives back an empty dictionary, so every caller can treat the result as
        a dictionary without special-casing.

    This is the single place the project parses a YAML config file, so the rest
    of the system never opens config files by hand.
    """
    path = Path(path)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as yaml_file:
        loaded = yaml.safe_load(yaml_file)
    if loaded is None:
        return {}
    return loaded


def load_settings(settings_path: Path = SETTINGS_PATH) -> Dict[str, Any]:
    """Load the global settings file (infrastructure, voice, turn-taking knobs).

    What goes in:
        settings_path: path to config/settings.yaml. Defaults to the canonical
        location at the project root.

    What comes out:
        A plain dictionary of every setting, for example API hosts, voice
        choices, and the maximum number of turns per call.

    Settings are required to run, so a missing file raises FileNotFoundError
    rather than returning an empty dictionary.
    """
    settings_path = Path(settings_path)
    if not settings_path.exists():
        raise FileNotFoundError(f"Settings file not found at {settings_path}")
    return _read_yaml_file(settings_path)


def load_scenario(scenario_path: Path) -> Dict[str, Any]:
    """Load one scenario file that describes a single test case.

    What goes in:
        scenario_path: path to a file under config/scenarios/.

    What comes out:
        A plain dictionary with the scenario fields: id, persona, goal, twist,
        knowledge_pack, steering, expected, severity_if_fails, and voice.

    A named scenario is required, so a missing file raises FileNotFoundError and
    leaves any fallback decision to the caller.
    """
    scenario_path = Path(scenario_path)
    if not scenario_path.exists():
        raise FileNotFoundError(f"Scenario file not found at {scenario_path}")
    return _read_yaml_file(scenario_path)


def load_knowledge_map(knowledge_map_path: Path = KNOWLEDGE_MAP_PATH) -> Dict[str, Any]:
    """Load the living knowledge map of what we know about the target agent.

    What goes in:
        knowledge_map_path: path to config/knowledge_map.yaml. Defaults to the
        canonical location at the project root.

    What comes out:
        A plain dictionary of accumulated intel about the target agent. This
        grows over time as the offline analysis folds in new findings.

    The map is optional, so a missing or empty file returns an empty dictionary
    and a first run still works before any intel has been gathered.
    """
    return _read_yaml_file(knowledge_map_path)
