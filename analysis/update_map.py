"""Fold new findings from a call into the living knowledge map.

The knowledge map is a config file that records what we have learned about the
medical receptionist AI across many calls: which facts it tends to get wrong,
which safety rules it has broken, which behaviors are already confirmed good.
The brain reads this map before each call so it can steer the patient toward the
weak spots instead of re-testing things we already understand.

This file is the writer side of that loop. After the analyzer grades a call, it
takes the new bug records and merges them into the existing map, then saves it.
The next call starts better informed than the last.
"""

from pathlib import Path
from typing import Any

from analysis.analyzer import AnalysisResult


def load_knowledge_map(map_path: Path) -> dict[str, Any]:
    """Read the current knowledge map from disk.

    Args:
        map_path: Path to the knowledge map file (a YAML file).

    Returns:
        The map as a dictionary. Returns an empty starter map if the file does
        not exist yet, so the first ever run still has something to write into.
    """
    # Steps the real version will take:
    #   1. If map_path does not exist, return a fresh empty map structure.
    #   2. Otherwise open the file and parse the YAML into a dictionary.
    #   3. Return the dictionary.
    raise NotImplementedError("load_knowledge_map is not implemented yet.")


def merge_findings(knowledge_map: dict[str, Any], result: AnalysisResult) -> dict[str, Any]:
    """Combine one call's findings into the existing knowledge map.

    This does not overwrite history. It adds the new findings, raises the count
    on repeated failures, and promotes confirmed good behavior, so the map
    reflects everything learned so far and not just the latest call.

    Args:
        knowledge_map: The current map, as returned by load_knowledge_map.
        result: The graded result of the call just finished.

    Returns:
        A new map dictionary with this call's findings folded in.
    """
    # Steps the real version will take:
    #   1. Walk every bug record in result.bug_records.
    #   2. For a failure, record or increment an entry under its oracle and topic
    #      so repeated failures stand out as priorities for the next call.
    #   3. For a pass, mark that behavior as confirmed good so we stop re-testing it.
    #   4. Return the updated map without losing earlier learnings.
    raise NotImplementedError("merge_findings is not implemented yet.")


def save_knowledge_map(knowledge_map: dict[str, Any], map_path: Path) -> None:
    """Write the updated knowledge map back to disk.

    Args:
        knowledge_map: The map to save, after merging the latest findings.
        map_path: Path to the knowledge map file to overwrite.

    Returns:
        Nothing. The map is written to map_path.
    """
    # Steps the real version will take:
    #   1. Convert the map dictionary to YAML text.
    #   2. Write it to map_path, replacing the old contents.
    raise NotImplementedError("save_knowledge_map is not implemented yet.")


def update_map_from_result(result: AnalysisResult, map_path: Path) -> dict[str, Any]:
    """Load the map, fold in one call's findings, and save it.

    This is the main entry point of the file. It ties the three steps together
    so the caller can update the living map in one line after grading a call.

    Args:
        result: The graded result of the call just finished.
        map_path: Path to the knowledge map file to read and update.

    Returns:
        The updated map dictionary that was written to disk.
    """
    # Steps the real version will take:
    #   1. Call load_knowledge_map to read the current map.
    #   2. Call merge_findings to fold in result.
    #   3. Call save_knowledge_map to persist the updated map.
    #   4. Return the updated map.
    raise NotImplementedError("update_map_from_result is not implemented yet.")
