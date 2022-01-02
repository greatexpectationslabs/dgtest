import sys
from configparser import ConfigParser
from typing import Callable, Dict, List, Optional, Tuple, Union

import click

from dgtest.cli.commands import list_dgtest_results, run_dgtest_results

# Configuration and options ============================================================================================


def configure(
    ctx: click.Context, param: Union[click.Option, click.Parameter], filename: str
) -> None:
    """Callback function to apply config file options to CLI commands (if present)

    Args:
        ctx: Click context used to pass on state on commands
        param: Unused but necessary to maintain signature
        filename: The configuration file

    Returns:
        Saves the config options in a dictionary within the Click context

    """
    cfg = ConfigParser()

    options: Dict[str, Union[str, List[str]]] = {}
    if not cfg.read(filename):
        return

    try:
        data = dict(cfg["options"])
        for key, value in data.items():
            # Necessary to convert INI lists into Python lists
            if "," in key:
                options[key] = [v.strip() for v in value.strip().split(",")]
            else:
                options[key] = value
        click.echo(f"Successfully read config values from {filename}: {options}")

    except KeyError:
        options = {}
        click.echo(
            f"Something went wrong when reading config values from {filename}; ignoring and using defaults"
        )

    ctx.default_map = options


def add_options(options: List[Callable]) -> Callable:
    """Decorator to apply shared options to all dgtest CLI commands

    Args:
        options: A list of Click options to be applied to any number of Click commands

    Returns:
        A callable function used to apply click.option decorators to a command

    """

    def _add_options(func: Callable) -> Callable:
        for option in reversed(options):
            func = option(func)
        return func

    return _add_options


# Options shared across ALL commands
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
        show_default=True,
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
    click.option(
        "-c",
        "--config",
        default="dgtest.ini",
        callback=configure,
        type=click.Path(dir_okay=False),
        is_eager=True,
        expose_value=False,
        help="Read option defaults from the specified config file",
        show_default=True,
    ),
]


# CLI commands =========================================================================================================


@click.group()
def cli() -> None:
    """
    Only test what you need to.
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
    """Command responsible for listing out the test files determined by the dgtest algorithm

    Args:
        source: The relative path to your source directory
        tests: The relative path to your tests directory
        depth: The depth of the graph traversal (the larger the number, the greater the coverage but the smaller the specificity)
        ignore_paths: Any test files that starts with any paths in this collection are ignored in the output
        filter_: Only test paths that start with this value are included in the output
        branch: The git branch to diff against

    Returns:
        Lists out results to STDOUT

    """
    list_dgtest_results(source, tests, depth, list(ignore_paths), filter_, branch)


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
        Lists out results to STDOUT and invokes pytest

    """
    code = run_dgtest_results(
        source, tests, depth, list(ignore_paths), filter_, branch, list(pytest_opts)
    )
    sys.exit(code)
