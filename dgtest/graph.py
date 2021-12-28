import json
from typing import Dict, List, Optional, Set, Tuple


def determine_tests_to_run(
    changed_source_files: List[str],
    changed_test_files: List[str],
    source_dependency_graph: Dict[str, Set[str]],
    tests_dependency_graph: Dict[str, Set[str]],
    depth: int,
    ignore_paths: Tuple[str],
    filter_: Optional[str],
) -> List[str]:
    # Identify which source files are relevant to the current commit
    relevant_source_files = determine_relevant_source_files(
        source_dependency_graph, changed_source_files, depth
    )

    # Use those source files and the dependency graphs to determine test candidates
    test_candidates = determine_test_candidates(
        tests_dependency_graph, relevant_source_files, changed_test_files
    )

    # Filter candidates down based on user args (if applicable)
    files_to_test = filter_test_candidates(test_candidates, ignore_paths, filter_)

    return files_to_test


def determine_relevant_source_files(
    source_dependency_graph: Dict[str, Set[str]],
    changed_source_files: List[str],
    depth: int,
) -> List[str]:
    relevant_source_files: Set[str] = set()
    for file in changed_source_files:
        deps = _traverse_graph(file, source_dependency_graph, depth)
        relevant_source_files.update(deps)
    return sorted(relevant_source_files)


def _traverse_graph(root: str, graph: Dict[str, Set[str]], depth: int) -> Set[str]:
    stack = [(root, depth)]
    seen: Set[str] = set()

    while stack:
        node, d = stack.pop()
        # If we've hit a cycle, traversed past our stated depth, or touched a file that isn't from our source, throw away the node
        if node in seen or d <= 0:
            continue
        seen.add(node)
        for child in graph.get(node, {}):
            stack.append((child, d - 1))

    return seen


def determine_test_candidates(
    tests_dependency_graph: Dict[str, Set[str]],
    source_files: List[str],
    changed_test_files: List[str],
) -> List[str]:
    # Ensure we include any test files that were identified in the git diff
    candidates = {file for file in changed_test_files}

    for file in source_files:
        for test in tests_dependency_graph.get(file, []):
            candidates.add(test)
    return sorted(candidates)


def filter_test_candidates(
    test_candidates: List[str], ignore_paths: Tuple[str], filter_: Optional[str] = None
) -> List[str]:
    filtered_tests = []
    for file in test_candidates:
        # Throw out files that are in our ignore list
        if any(file.startswith(path) for path in ignore_paths):
            continue
        # Throw out files that aren't explicitly part of a filter (if supplied)
        if filter_ and not file.startswith(filter_):
            continue
        filtered_tests.append(file)
    return filtered_tests


def prettify_graphs(*graphs: Tuple[str, Dict[str, Set[str]]]) -> str:
    prettified_graphs = []
    for title, data in graphs:
        prettified_graph = {title: {k: sorted(v) for k, v in data.items()}}
        prettified_graphs.append(prettified_graph)

    output = json.dumps(prettified_graphs, sort_keys=True, indent=2)
    return output
