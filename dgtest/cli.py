import sys
from typing import Callable, List, Optional, Tuple

import click

from dgtest.main import determine_test_list, run_tests


@click.group()
def cli() -> None:
    pass


shared_options = [
    click.option(
        "-t",
        "--tests",
        "tests",
        help="The relative path to your tests directory (if applicable)",
        type=click.Path(exists=True),
    ),
    click.option(
        "-d",
        "--depth",
        "depth",
        help="The desired maximum depth of the graph traversal algorithm",
        default=3,
        type=int,
    ),
    click.option(
        "-i",
        "--ignore",
        "ignore_paths",
        help="Exclude results that begin with any provided path prefix",
        type=click.Path(),
        multiple=True,
    ),
    click.option(
        "-f",
        "--filter",
        "filter_",
        help="Filter results to only include those that being with the provided path prefix",
        type=click.Path(),
    ),
    click.option(
        "-b",
        "--branch",
        "branch",
        help="The specific branch to diff against",
        type=str,
    ),
]


def add_options(options: List[Callable]) -> Callable:
    def _add_options(func: Callable) -> Callable:
        for option in reversed(options):
            func = option(func)
        return func

    return _add_options


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
    files_to_test = determine_test_list(
        source, tests, depth, list(ignore_paths), filter_, branch
    )

    for file in files_to_test:
        click.echo(file)


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
@click.argument("pytest_args", nargs=-1, type=click.UNPROCESSED)
def run_command(
    source: str,
    tests: Optional[str],
    depth: int,
    ignore_paths: Tuple[str],
    filter_: Optional[str],
    branch: Optional[str],
    pytest_args: Tuple[str],
) -> None:
    exit_code = run_tests(
        source, tests, depth, list(ignore_paths), filter_, branch, list(pytest_args)
    )
    sys.exit(exit_code)
