<h3 align="center">dgtest</h3>

<p align="center">
<a href="https://asciinema.org/a/kUYvSCoqbtrddwgYigoPKOSHc?autoplay=1">
    <img src="https://asciinema.org/a/kUYvSCoqbtrddwgYigoPKOSHc.png" width="80%"/>
</a>
</p>

---

#### Background

`dgtest` aims to improve the performance of your test runs by only selecting relevant tests based on your Git state.
Using AST parsing, `dgtest` creates dependency graphs out of your codebase and uses traditional graph traversal algorithms to select the smallest possible
subset of the test suite required to obtain coverage over a given commit or PR.

Note that this is designed to be used in tandem with your current testing strategy. `dgtest` provides a high level of accuracy but ultimately is a static
analysis tool and relies heavily on adherence to Pythonic conventions (namely imports as discussed in the [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html#224-decision0)).
If you use this tool, ensure you still run the full suite every so often.

Note that `dgtest` only works with codebases that use `pytest` as a testing framework; due to the way the tool parses
`pytest` fixtures and tests, usage with `nose` or `unittest` will not work as intended.

---

#### Installation

The get started, install the CLI tool using:
```
pip install dgtest
```

`dgtest` uses the following dependencies under the hood:
* [Click](https://github.com/pallets/click)
* [GitPython](https://github.com/gitpython-developers/GitPython)
* [pytest](https://github.com/pytest-dev/pytest)

---

#### Usage

`dgtest` has a minimal API by design:

```
Commands:
  list  Print list of determined test files
  run   Run determined test files with pytest
```

`list` outputs the result of `dgtest`'s underlying algorithm while `run` actually runs them with `pytest`.

The following options are shared between both commands:
```
-t, --tests   The relative path to your test directory (if applicable)
-d, --depth   The desired maximum depth of the graph traversal algorithm (default: 3)
-i, --ignore  A list of path prefixes that should be ignored
-f, --filter  Isolates results to only include those with the given path prefix
-b, --branch  The specific branch to `git diff` against - can be local or remote
-c, --config  Where to read config options from (default: dgtest.ini if it exists)
```

Additionally, note that `run` accepts any `pytest` flags (including extensions) that you may have set in your project:
```bash
# Spark and Postgres flags are specific to the Great Expectations project
dgtest run great_expectations -t tests -b "origin/develop" --no-spark --no-postgresql

# Coverage is a pytest extension
dgtest run great_expectations -t tests --cov=great_expectations
```

---

#### Config

In the case you use the same options over and over again, you can set a `dgtest.ini` file to save your configuration.
If the option is a list, please use a comma-delimited string.
```ini
[options]
tests = tests
depth = 2
ignore = foo, bar
filter = baz
branch = origin/develop
```

This changes the following command:
```bash
dgtest list great_expectations -t tests -d 2 -i foo -i bar -f baz -b "origin/develop"
```
to this:
```bash
dgtest list great_expectations
```

Any values passed into a command-line invocation will take priority over the config file's variables.

If you'd like to set up `dgtest` as part of your PyCharm workflow:
1. Navigate to **Run** -> **Edit Configurations** within your menu bar
2. Click the **+** icon and add a new **Python** configuration
3. Copy the following config options and click **Apply** and **Ok**:

![PyCharm Config](assets/pycharm_config.png)
*Note that the `dgtest` options (`-t` and `-b`) are not strictly necessary if they are configured in a `dgtest.ini` file.*
