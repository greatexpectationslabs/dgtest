import sys
from typing import List, Optional, Tuple

import click
import pytest

from dgtest.filesystem import get_changed_files
from dgtest.graph import determine_tests_to_run
from dgtest.opts import add_options, shared_options
from dgtest.parse import get_dependency_graphs


@click.group()
def cli() -> None:
    """
    Welcome to dgtest!
    """
    pass


@cli.command(
    name="list",
    help="Print list of determined test files",
)
@add_options(shared_options)
@click.argument(
    "source",
    type=click.Path(exists=True),
)
def list_command(
    source: str,
    tests: Optional[str],
    depth: int,
    ignore_paths: Tuple[str],
    filter_: Optional[str],
    branch: Optional[str],
) -> None:
    """
    TODO(cdkini): Write docstr!

    """
    _list(source, tests, depth, list(ignore_paths), filter_, branch)


@cli.command(
    name="run",
    help="Run determined test files with pytest",
    context_settings=dict(ignore_unknown_options=True),
)
@add_options(shared_options)
@click.argument(
    "source",
    type=click.Path(exists=True),
)
@click.argument("pytest_opts", nargs=-1, type=click.UNPROCESSED)
def run_command(
    source: str,
    tests: Optional[str],
    depth: int,
    ignore_paths: Tuple[str],
    filter_: Optional[str],
    branch: Optional[str],
    pytest_opts: Tuple[str],
) -> None:
    """
    TODO(cdkini): Write docstr!

    """
    files_to_test = _list(source, tests, depth, list(ignore_paths), filter_, branch)
    exit_code = _run(files_to_test, list(pytest_opts))
    sys.exit(exit_code)


def _list(
    source: str,
    tests: Optional[str],
    depth: int,
    ignore_paths: List[str],
    filter_: Optional[str],
    branch: Optional[str],
) -> List[str]:
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

    click.echo("Files identified by dgtest:")
    if not files_to_test:
        click.echo("  No tests to run!")
    else:
        for file in files_to_test:
            click.echo(f"  {file}")

    return files_to_test


def _run(
    files_to_test: List[str],
    pytest_opts: List[str],
) -> int:
    if len(files_to_test) == 0:
        click.echo("No tests to run!")
        return 0

    exit_code = pytest.main(files_to_test + pytest_opts)
    return exit_code
