import pathlib
from typing import Callable, Dict, List, Set, Tuple

import py
import pytest

from dgtest.parse import (
    parse_definition_nodes_from_codebase,
    parse_definition_nodes_from_file,
    parse_import_nodes_from_codebase,
    parse_import_nodes_from_file,
    parse_pytest_fixtures_from_file,
    parse_pytest_tests_from_codebase,
    parse_pytest_tests_from_file,
    update_dict,
)


@pytest.fixture(scope="function")
def create_mock_codebase(tmpdir: py.path.local) -> Callable:
    def _create_mock_codebase(
        directory: str, *files: Tuple[str, str]
    ) -> Tuple[str, List[str]]:
        my_dir = tmpdir.mkdir(directory)
        my_files = []
        for name, contents in files:
            temp_file = my_dir.join(name)
            temp_file.write(contents)
            my_files.append(temp_file.strpath)
        return my_dir.strpath, my_files

    return _create_mock_codebase


@pytest.fixture(scope="function")
def definition_map() -> Dict[str, Set[str]]:
    return {
        "my_first_func": {"my_package/util/file.py"},
        "my_second_func": {"my_package/core/util.py"},
        "my_third_func": {"my_package/core/util.py"},
        "MyClassA": {"my_package/core/my_class.py"},
        "MyClassB": {"my_package/core/my_class.py"},
    }


@pytest.fixture(scope="function")
def fixture_map() -> Dict[str, Set[str]]:
    return {"prepare_classes": {"my_package/core/my_class.py"}}


def test_parse_definition_nodes_from_file_collects_function_definitions(
    create_mock_codebase: Callable,
) -> None:

    file_contents = """
def my_first_func():
    pass

def my_second_func():
    pass
    """

    _, my_files = create_mock_codebase("my_dir", ("my_file1.py", file_contents))
    file_definition_map = parse_definition_nodes_from_file(my_files[0])

    assert len(file_definition_map) == 2
    assert (
        isinstance(file_definition_map["my_first_func"], set)
        and len(file_definition_map["my_first_func"]) == 1
    )
    assert (
        isinstance(file_definition_map["my_second_func"], set)
        and len(file_definition_map["my_second_func"]) == 1
    )


def test_parse_definition_nodes_from_file_collects_class_definitions(
    create_mock_codebase: Callable,
) -> None:
    file_contents = """
class Bar:
    pass

class Baz:
    def __init__(self, a: int, b: int):
        self.a = a
        self.b = b
    """
    _, my_files = create_mock_codebase("my_dir", ("my_file1.py", file_contents))
    definition_map = parse_definition_nodes_from_file(my_files[0])

    assert len(definition_map) == 2
    assert (
        isinstance(definition_map["Bar"], set) and my_files[0] in definition_map["Bar"]
    )
    assert (
        isinstance(definition_map["Baz"], set) and my_files[0] in definition_map["Baz"]
    )


def test_parse_definition_nodes_from_codebase_accounts_for_namespace_collision(
    create_mock_codebase: Callable,
) -> None:

    file_contents1 = """
class Foo:
    pass
    """
    file_contents2 = """
class Foo:
    def __init__(self, a: int, b: int):
        self.a = a
        self.b = b
    """

    _, my_files = create_mock_codebase(
        "my_dir", ("my_file1.py", file_contents1), ("my_file2.py", file_contents2)
    )
    definition_map = parse_definition_nodes_from_codebase(my_files)

    assert len(definition_map) == 1
    assert isinstance(definition_map["Foo"], set) and len(definition_map["Foo"]) == 2


def test_parse_import_nodes_from_file_with_no_relative_imports(
    create_mock_codebase: Callable,
) -> None:
    file_contents = """
import copy
import datetime
import json
import logging
import os
from typing import Dict, List, Optional, Union
from uuid import UUID
    """
    _, my_files = create_mock_codebase("my_dir", ("my_file1.py", file_contents))

    imports = parse_import_nodes_from_file(my_files[0], "my_package", {})
    assert imports == set()


def test_parse_import_nodes_from_file_with_relative_imports(
    create_mock_codebase: Callable,
    definition_map: Dict[str, Set[str]],
) -> None:
    file_contents = """
from my_package.util import my_first_func
from my_package.core import MyClassA
from my_package.core.util import my_second_func, my_third_func
    """

    _, my_files = create_mock_codebase("my_dir", ("my_file.py", file_contents))
    imports = parse_import_nodes_from_file(my_files[0], "my_package", definition_map)

    assert len(imports) == 3
    assert all(
        path in imports
        for path in (
            "my_package/util/file.py",
            "my_package/core/my_class.py",
            "my_package/core/util.py",
        )
    )


def test_parse_import_nodes_from_file_with_ambiguous_imports(
    create_mock_codebase: Callable,
) -> None:
    file_contents = """
from my_package.util import my_first_func
    """
    _, my_files = create_mock_codebase("my_dir", ("my_file.py", file_contents))

    # Namespace collision means we need to pick the closest import
    definition_map = {
        "my_first_func": {"my_package/util/file.py", "my_package/core/file.py"},
    }

    imports = parse_import_nodes_from_file(my_files[0], "my_package", definition_map)
    assert len(imports) == 1

    # The import statement included "util" so we pick the first option
    assert "my_package/util/file.py" in imports
    assert "my_package/core/file.py" not in imports


def test_parse_import_nodes_from_codebase(
    create_mock_codebase: Callable, definition_map: Dict[str, Set[str]]
) -> None:
    file_contents1 = """
import copy
import datetime
import json
import logging

from my_package.core import MyClassA
from my_package.util import my_first_func
    """
    file_contents2 = """
import pandas as pd
import numpy as np
import os

from my_package.core import MyClassB
from my_package.core.util import my_second_func, my_third_func
    """

    _, my_files = create_mock_codebase(
        "my_dir", ("my_file1.py", file_contents1), ("my_file2.py", file_contents2)
    )
    imports = parse_import_nodes_from_codebase(my_files, "my_package", definition_map)
    print(imports)

    assert len(imports) == 3
    keys = [
        "my_package/util/file.py",
        "my_package/core/util.py",
        "my_package/core/my_class.py",
    ]
    assert all(file in imports for file in keys)
    assert len(imports["my_package/util/file.py"]) == 1  # Only imported by my_file1
    assert len(imports["my_package/core/util.py"]) == 1  # Only imported by my_file2
    assert len(imports["my_package/core/my_class.py"]) == 2  # Imported in both files


def test_parse_pytest_fixtures_from_file_with_simple_fixtures(
    create_mock_codebase: Callable,
) -> None:
    file_contents = """
@pytest.fixture()
def my_fixture1():
    pass

@pytest.fixture()
def my_fixture2():
    pass
    """
    _, my_files = create_mock_codebase("my_dir", ("conftest.py", file_contents))

    imports = parse_pytest_fixtures_from_file(my_files[0], {})
    assert imports == {}


def test_parse_pytest_fixtures_from_file_with_fixtures_referencing_symbols(
    create_mock_codebase: Callable,
    definition_map: Dict[str, Set[str]],
) -> None:
    file_contents = """
@pytest.fixture()
def my_fixture():
    my_class = MyClassA()
    my_first_func(my_class)
    return my_class
    """

    _, my_files = create_mock_codebase("my_dir", ("conftest.py", file_contents))
    imports = parse_pytest_fixtures_from_file(my_files[0], definition_map)

    assert len(imports) == 1
    assert imports["my_fixture"] == {
        "my_package/core/my_class.py",
        "my_package/util/file.py",
    }


# FIXME(cdkini): This functionality needs to be enabled!
# def test_parse_pytest_fixtures_from_file_with_fixtures_referencing_each_other(
#     create_mock_codebase: Callable,
#     definition_map: Dict[str, Set[str]],
# ) -> None:
#     file_contents = """
# @pytest.fixture()
# def my_fixture1():
#     my_class = MyClassA()
#     my_first_func(my_class)
#     return my_class


# @pytest.fixture()
# def my_fixture2(my_fixture1): # This should share 'my_fixture1's dependencies
#     return my_fixture1
#     """

#     _, my_files = create_mock_codebase("my_dir", ("conftest.py", file_contents))
#     imports = parse_pytest_fixtures_from_file(my_files[0], definition_map)

#     assert len(imports) == 2
#     assert imports["my_fixture1"] == {
#         "my_package/core/my_class.py",
#         "my_package/util/file.py",
#     }
#     assert imports["my_fixture2"] == {
#         "my_package/core/my_class.py",
#         "my_package/util/file.py",
#     }


# TODO(cdkini): Open to write test for this method!
# def test_parse_pytest_fixtures_from_codebase(tmpdir: py.path.local) -> None:
#     pass  # TBD


def test_parse_pytest_tests_from_file_with_imports(
    create_mock_codebase: Callable, definition_map: Dict[str, Set[str]]
) -> None:
    test_file_name = "test_my_class.py"
    file_contents = """
from my_package.core import MyClassA, MyClassB

def test_MyClassA():
    assert MyClassA()

def test_MyClassB():
    assert MyClassB()
    """

    _, my_files = create_mock_codebase("my_dir", (test_file_name, file_contents))
    file_graph = parse_pytest_tests_from_file(
        my_files[0], "my_package", definition_map, fixture_map={}
    )

    assert len(file_graph) == 1
    assert len(file_graph["my_package/core/my_class.py"]) == 1
    assert list(file_graph["my_package/core/my_class.py"])[0].endswith(
        "test_my_class.py"
    )


def test_parse_pytest_tests_from_file_with_fixtures(
    create_mock_codebase: Callable,
    definition_map: Dict[str, Set[str]],
    fixture_map: Dict[str, Set[str]],
) -> None:
    test_file_name = "test_my_class.py"
    file_contents = """
def test_my_classes(prepare_classes):
    pass
"""

    _, my_files = create_mock_codebase("my_dir", (test_file_name, file_contents))

    file_graph = parse_pytest_tests_from_file(
        my_files[0], "my_package", definition_map, fixture_map
    )

    assert len(file_graph) == 1
    assert len(file_graph["my_package/core/my_class.py"]) == 1
    assert list(file_graph["my_package/core/my_class.py"])[0].endswith(
        "test_my_class.py"
    )


def test_parse_pytest_tests_from_file_with_imports_and_fixtures(
    create_mock_codebase: Callable,
    definition_map: Dict[str, Set[str]],
    fixture_map: Dict[str, Set[str]],
) -> None:
    test_file_name = "test_my_class.py"
    file_contents = """
from my_package.core import MyClassA
from my_package.util import my_first_func


def test_my_classes(prepare_classes):
    pass
"""

    _, my_files = create_mock_codebase("my_dir", (test_file_name, file_contents))
    file_graph = parse_pytest_tests_from_file(
        my_files[0], "my_package", definition_map, fixture_map
    )

    assert len(file_graph) == 2
    for file in ("my_package/core/my_class.py", "my_package/util/file.py"):
        assert len(file_graph[file]) == 1
        assert list(file_graph[file])[0].endswith("test_my_class.py")


def test_parse_pytest_tests_from_codebase(
    create_mock_codebase: Callable,
    definition_map: Dict[str, Set[str]],
    fixture_map: Dict[str, Set[str]],
) -> None:
    file_contents1 = """
from my_package.core import MyClassA
from my_package.util import my_first_func

def test_my_classes(prepare_classes):
    pass
    """
    file_contents2 = """
from my_package.util import my_first_func

@pytest.fixture()
def my_fixture():
    return my_first_func()

def test_my_classes(fake_fixture, my_fixture):
    pass
    """

    _, my_files = create_mock_codebase(
        "my_dir", ("test_file1.py", file_contents1), ("test_file2.py", file_contents2)
    )

    tests_dependency_graph = parse_pytest_tests_from_codebase(
        my_files, "my_package", definition_map, fixture_map
    )

    assert len(tests_dependency_graph) == 2
    assert len(tests_dependency_graph["my_package/core/my_class.py"]) == 1
    assert len(tests_dependency_graph["my_package/util/file.py"]) == 2


def test_update_dict_updates_existing_keys() -> None:
    A = {"my_file1": {"a", "b", "c"}}
    B = {"my_file1": {"c", "d", "e"}}

    update_dict(A, B)

    assert len(A) == 1
    assert all(num in A["my_file1"] for num in ("a", "b", "c", "d", "e"))


def test_update_dict_adds_new_keys() -> None:
    A = {"my_file1": {"a", "b", "c"}}
    B = {"bar": {"c", "d", "e"}}

    update_dict(A, B)

    assert len(A) == 2
    assert all(num in A["my_file1"] for num in ("a", "b", "c"))
    assert all(num in A["bar"] for num in ("c", "d", "e"))
