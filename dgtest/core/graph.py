from typing import Dict, List, Optional, Set


def determine_tests_to_run(
    changed_source_files: List[str],
    changed_test_files: List[str],
    source_dependency_graph: Dict[str, Set[str]],
    tests_dependency_graph: Dict[str, Set[str]],
    depth: int,
    ignore_paths: List[str],
    filter_: Optional[str],
) -> List[str]:
    """Wrapper method that encapsulates all graph traversal behavior.

    Args:
        changed_source_files: A collection of source files that are relevant to the current commit/PR
        changed_test_files: A colleciton of test files that are relevant to the current commit/PR
        source_dependency_graph: A mapping between source files and the other source files that import it (see `parse_import_nodes_from_codebase`)
        tests_dependency_graph: A mapping between source files and the relevant test files needed to gain coverage (see `parse_pytest_tests_from_codebase`)
        depth: The depth of the graph traversal (the larger the number, the greater the coverage but the smaller the specificity)
        ignore_paths: Any test files that starts with any paths in this collection are ignored in the output
        filter_: Only test paths that start with this value are included in the output

    Returns:
        A finalized list of tests that are necessary to obtain coverage over the changed source/test files

    """
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
    """Determines which source files should be evaluated by the dependency graph traversal algorithm

    Args:
        source_dependency_graph: A mapping between source files and the other source files that import it (see `parse_import_nodes_from_codebase`)
        changed_source_files: A collection of source files that are relevant to the current commit/PR
        depth: The depth of the graph traversal (the larger the number, the greater the coverage but the smaller the specificity)

    Returns:
        A list of relevant source files

    """
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
        # If we've hit a cycle or traversed past our stated depth, throw away the node
        if node in seen or d <= 0:
            continue
        seen.add(node)
        # Sorting is required to ensure the same results each time (lack of ordering in sets can result in different paths)
        children = graph.get(node, set())
        for child in sorted(children):
            stack.append((child, d - 1))

    return seen


def determine_test_candidates(
    tests_dependency_graph: Dict[str, Set[str]],
    relevant_source_files: List[str],
    changed_test_files: List[str],
) -> List[str]:
    """Determines a list of test files that should be run to cover a set of changed source files

    These are the raw results and will need to undergo further processing before a finalized
    list can be provided to the user.

    Args:
        tests_dependency_graph: A mapping between source files and the relevant test files needed to gain coverage (see `parse_pytest_tests_from_codebase`)
        relevant_source_files: The output list of source files determined by `determine_relevant_source_files`
        changed_test_files: A colleciton of test files that are relevant to the current commit/PR

    Returns:
        A list of test file candidates that will possibly be part of the final output

    """
    # Ensure we include any test files that were identified in the git diff
    candidates = {file for file in changed_test_files}

    for file in relevant_source_files:
        tests: Set[str] = tests_dependency_graph.get(file, set())
        for test in tests:
            candidates.add(test)
    return sorted(candidates)


def filter_test_candidates(
    test_candidates: List[str], ignore_paths: List[str], filter_: Optional[str]
) -> List[str]:
    """Filters a series of test candidates down to the final output

    Uses a number of user-provided criteria (filters and ignores) to narrow down the
    list of candidates.

    Args:
        tests_candidates: The output list of test files determined by `filter_test_candidates`
        ignore_paths: Any test files that starts with any paths in this collection are ignored in the output
        filter_: Only test paths that start with this value are included in the output

    Returns:
        The final list of tests to be run. This is the end result of the full dgtest algorithm.

    """
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
