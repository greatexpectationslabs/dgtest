from typing import List, Optional

import click
import pytest

from dgtest.core.fs import get_changed_files
from dgtest.core.graph import determine_tests_to_run
from dgtest.core.parse import get_dependency_graphs


def list_dgtest_results(
    source: str,
    tests: Optional[str],
    depth: int,
    ignore_paths: List[str],
    filter_: Optional[str],
    branch: Optional[str],
) -> List[str]:
    """Command responsible for listing out the test files determined by the dgtest algorithm

    Args:
        source: The relative path to your source directory
        tests: The relative path to your tests directory
        depth: The depth of the graph traversal (the larger the number, the greater the coverage but the smaller the specificity)
        ignore_paths: Any test files that starts with any paths in this collection are ignored in the output
        filter_: Only test paths that start with this value are included in the output
        branch: The git branch to diff against

    Returns:
        A list of test results from your test suite

    """
    changed_source_files, changed_test_files = get_changed_files(branch)
    source_dependency_graph, tests_dependency_graph = get_dependency_graphs(
        source, tests
    )

    # Test dependency graph will be empty if no tests are present
    if not tests_dependency_graph and not tests:
        click.echo(
            "No test files were parsed; if using an external tests directory, please ensure you pass it in with `-t`"
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

    click.echo("Test files identified by dgtest:")
    if not files_to_test:
        click.echo("  No tests to run!")
    else:
        for file in files_to_test:
            click.echo(f"  {file}")

    return files_to_test


def run_dgtest_results(
    source: str,
    tests: Optional[str],
    depth: int,
    ignore_paths: List[str],
    filter_: Optional[str],
    branch: Optional[str],
    pytest_opts: List[str],
) -> int:
    """Command responsible for running the test files determined by the dgtest algorithm

    Args:
        source: The relative path to your source directory
        tests: The relative path to your tests directory
        depth: The depth of the graph traversal (the larger the number, the greater the coverage but the smaller the specificity)
        ignore_paths: Any test files that starts with any paths in this collection are ignored in the output
        filter_: Only test paths that start with this value are included in the output
        branch: The git branch to diff against
        pytest_opts: Any pytest flags, options, or args -- note that they may not collide with a dgtest option

    Returns:
        A status code (non-zero signifying a failure)

    """
    files_to_test = list_dgtest_results(
        source, tests, depth, ignore_paths, filter_, branch
    )
    if len(files_to_test) == 0:
        return 0

    status_code = pytest.main(files_to_test + pytest_opts)
    # Exit code 5: No tests were collected (we want to treat this as a pass)
    if status_code == 5:
        status_code = 0

    return status_code
