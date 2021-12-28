from typing import List, Optional

import click

from dgtest.graph import determine_tests_to_run, prettify_graphs
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
@click.argument("source", type=click.Path(exists=True))
def run(
    source: str,
    tests: Optional[str],
    depth: int,
    ignore_paths: List[str],
    filter_: Optional[str],
    branch: str,
) -> None:
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

    for file in files_to_test:
        click.echo(file)


@cli.command(help="Print dependency graphs")
@click.option(
    "-t",
    "--tests",
    "tests",
    help="The relative path to your tests directory (if applicable)",
    type=click.Path(exists=True),
)
@click.argument("source", type=click.Path(exists=True))
def graph(
    source: str,
    tests: Optional[str],
) -> None:
    source_dependency_graph, tests_dependency_graph = get_dependency_graphs(
        source, tests
    )

    stringified_graph = prettify_graphs(
        ("Source Dependency Graph", source_dependency_graph),
        ("Tests Dependency Graph", tests_dependency_graph),
    )

    print(stringified_graph)


@cli.command(help="Preview test runs")
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
@click.argument("source", type=click.Path(exists=True))
def preview(
    source: str,
    tests: Optional[str],
    depth: int,
) -> None:
    source_dependency_graph, tests_dependency_graph = get_dependency_graphs(
        source, tests
    )

    for file in source_dependency_graph:
        files_to_test = determine_tests_to_run(
            changed_source_files=[file],
            changed_test_files=[],
            source_dependency_graph=source_dependency_graph,
            tests_dependency_graph=tests_dependency_graph,
            depth=depth,
            ignore_paths=[],
            filter_=None,
        )
        print(file, files_to_test)
