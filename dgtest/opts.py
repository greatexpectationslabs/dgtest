from configparser import ConfigParser
from typing import Callable, Dict, List, Union

import click


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
    cfg.read(filename)
    try:
        options: Dict[str, Union[str, List[str]]] = {}
        data = dict(cfg["options"])

        for key, value in data.items():
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
