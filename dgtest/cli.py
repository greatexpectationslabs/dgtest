from typing import List, Optional

import click

from dgtest.graph import determine_tests_to_run
from dgtest.parse import get_dependency_graphs
from dgtest.utils import get_changed_files


@click.group()
def cli() -> None:
    pass


@cli.command(help="Run dependency graph test runner")
@click.option(
    "-t",
    "--tests",
    "tests",
    help="The relative path to your tests directory (if applicable)",
    type=click.Path(exists=True),
)
@click.option(
    "-d",
    "--depth",
    "depth",
    help="The desired maximum depth of the graph traversal algorithm",
    default=3,
    type=int,
)
@click.option(
    "-i",
    "--ignore",
    "ignore_paths",
    help="Exclude results that begin with any provided path prefix",
    default=[],
    type=list,
)
@click.option(
    "-f",
    "--filter",
    "filter_",
    help="Filter results to only include those that being with the provided path prefix",
    type=click.Path(),
)
@click.option(
    "-b",
    "--branch",
    "branch",
    help="The specific branch to diff against",
    default="origin/develop",
    type=str,
)
@click.option(
    "-o",
    "--output",
    "output",
    help="Where you'd like to write the results to",
    type=click.Path(),
)
@click.argument("source", type=click.Path(exists=True))
def run(
    source: str,
    tests: Optional[str],
    depth: int,
    ignore_paths: List[str],
    filter_: Optional[str],
    branch: str,
    output: Optional[str],
) -> None:
    changed_files = get_changed_files(branch)
    source_dependency_graph, tests_dependency_graph = get_dependency_graphs(
        source, tests
    )
    files_to_test = determine_tests_to_run(
        changed_files,
        source_dependency_graph,
        tests_dependency_graph,
        depth,
        ignore_paths,
        filter_,
    )

    for file in files_to_test:
        click.echo(file)