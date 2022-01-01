<h3 align="center">dgtest</h3>

<p align="center">
<a href="https://asciinema.org/a/kUYvSCoqbtrddwgYigoPKOSHc?autoplay=1">
    <img src="https://asciinema.org/a/kUYvSCoqbtrddwgYigoPKOSHc.png" width="80%"/>
</a>
</p>

---

#### Background

`dgtest` aims to improve the performance of your test runs without sacrificing the safety of your test suite.
Using AST parsing, `dgtest` creates dependency graphs out of your codebase and uses traditional graph algorithms to select only the most important test files to obtain coverage over a given commit or PR.

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
-c, --config  Where to read config options from (default: dgtest.ini)
```

Additionally, note that `run` accepts any `pytest` flags or extensions you may have set in your project as follows:
```bash
# Spark and Postgres flags are specific to the Great Expectations project
dgtest run great_expectations/ -t tests -b "origin/develop" --no-spark --no-postgresql
```

---

#### Config

In the case you use the same options over and over again, you can set a `dgtest.ini` file to save your configuration.
If the option is a list, please use a comma-delimited string.
```ini
[options]
tests = tests/
depth = 2
ignore = foo/, bar/
filter = baz/
branch = origin/develop
```

This changes the following command:
```bash
dgtest list great_expectations/ -t tests -i foo/ -i bar -f baz/ -b "origin/develop"
```
to this:
```bash
dgtest list great_expectations/
```

Any values passed into a command-line invocation will take priority over the config file's variables.
