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
    """
    TODO(cdkini): Write docstr!

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
    """
    TODO(cdkini): Write docstr!

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
