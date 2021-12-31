from typing import List, Optional

import pytest

from dgtest.filesystem import get_changed_files
from dgtest.graph import determine_tests_to_run
from dgtest.parse import get_dependency_graphs


def determine_test_list(
    source: str,
    tests: Optional[str],
    depth: int,
    ignore_paths: List[str],
    filter_: Optional[str],
    branch: Optional[str],
) -> List[str]:
    """Command used to run dependency graph test strategy on a target codebase.

    Args:
        source: The relative path to your source directory
        tests: The relative path to your tests directory
        depth: The depth of the graph traversal (the larger the number, the greater the coverage but the smaller the specificity)
        ignore_paths: Any test files that starts with any paths in this collection are ignored in the output
        filter_: Only test paths that start with this value are included in the output
        branch: The specific branch to diff against to determine changed files

    Returns:
        A list of test files to run

    """
    changed_source_files, changed_test_files = get_changed_files(branch)
    source_dependency_graph, tests_dependency_graph = get_dependency_graphs(
        source, tests
    )
    files_to_test = determine_tests_to_run(
        changed_source_files,
        changed_test_files,
        source_dependency_graph,
        tests_dependency_graph,
        depth,
        ignore_paths,
        filter_,
    )

    return files_to_test


def run_tests(
    files_to_test: List[str],
    pytest_opts: List[str],
) -> int:
    """
    TODO(cdkini): Write docstr!

    """
    if len(files_to_test) == 0:
        print("No tests to run!")
        return 0

    exit_code = pytest.main(files_to_test + pytest_opts)
    return exit_code
