from typing import Dict, List, Optional, Set


def determine_relevant_source_files(
    source_dependency_graph: Dict[str, Set[str]], changed_files: List[str], depth: int
) -> List[str]:
    relevant_source_files: Set[str] = set()
    for file in changed_files:
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


def determine_tests_to_run(
    test_candidates: List[str], ignore_paths: List[str], filter_: Optional[str] = None
) -> List[str]:
    files_to_test = []
    for file in test_candidates:
        # Throw out files that are in our ignore list
        if any(file.startswith(path) for path in ignore_paths):
            continue
        # Throw out files that aren't explicitly part of a filter (if supplied)
        if filter_ and not file.startswith(filter_):
            continue
        files_to_test.append(file)
    return files_to_test
