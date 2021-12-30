from typing import Callable, Dict, List, Set, Tuple

import py
import pytest

from dgtest.parse import (
    parse_definition_nodes_from_codebase,
    parse_definition_nodes_from_file,
    parse_import_nodes_from_codebase,
    parse_import_nodes_from_file,
    parse_pytest_fixtures_from_codebase,
    parse_pytest_fixtures_from_file,
    parse_pytest_tests_from_codebase,
    parse_pytest_tests_from_file,
    update_dict,
)


@pytest.fixture(scope="function")
def create_mock_codebase(tmpdir: py.path.local) -> Callable:
    """Utility to easily create temporary filesystems"""

    def _create_mock_codebase(
        directory: str, *files: Tuple[str, str]
    ) -> Tuple[str, List[str]]:
        # Create source and tests directories
        my_dir = tmpdir.mkdir(directory)
        my_dir.mkdir("tests")

        my_files = []
        for name, contents in files:
            temp_file = my_dir.join(name)
            temp_file.write(contents)
            my_files.append(temp_file.strpath)
        return my_dir.strpath, my_files

    return _create_mock_codebase


@pytest.fixture(scope="function")
def definition_map() -> Dict[str, Set[str]]:
    """Used to represent the result of `parse_definition_nodes_from_codebase`"""
    return {
        "reverse_string": {"my_package/strings/strings.py"},
        "concatenate_strings": {"my_package/strings/strings.py"},
        "add_two_numbers": {"my_package/math/addition.py"},
        "Square": {"my_package/math/geometry.py"},
        "Triangle": {"my_package/math/geometry.py"},
    }


@pytest.fixture(scope="function")
def fixture_map() -> Dict[str, Set[str]]:
    """Used to represent the result of `parse_pytest_fixtures_from_codebase`"""
    return {"create_shapes": {"my_package/math/geometry.py"}}


def test_parse_definition_nodes_from_file_collects_function_definitions(
    create_mock_codebase: Callable,
) -> None:

    file_contents = """
def add_two_numbers(x, y):
    return x + y

def reverse_string(string):
    return string.reverse()
    """

    _, my_files = create_mock_codebase("my_dir", ("my_file1.py", file_contents))
    file_definition_map = parse_definition_nodes_from_file(my_files[0])

    assert len(file_definition_map) == 2
    assert (
        isinstance(file_definition_map["add_two_numbers"], set)
        and len(file_definition_map["add_two_numbers"]) == 1
    )
    assert (
        isinstance(file_definition_map["reverse_string"], set)
        and len(file_definition_map["reverse_string"]) == 1
    )


def test_parse_definition_nodes_from_file_collects_class_definitions(
    create_mock_codebase: Callable,
) -> None:
    file_contents = """
class Square(Shape):
    pass

class Triangle(Shape):
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z
    """
    _, my_files = create_mock_codebase("my_dir", ("my_file1.py", file_contents))
    definition_map = parse_definition_nodes_from_file(my_files[0])

    assert len(definition_map) == 2
    assert (
        isinstance(definition_map["Square"], set)
        and my_files[0] in definition_map["Square"]
    )
    assert (
        isinstance(definition_map["Triangle"], set)
        and my_files[0] in definition_map["Triangle"]
    )


def test_parse_definition_nodes_from_codebase_accounts_for_namespace_collision(
    create_mock_codebase: Callable,
) -> None:

    file_contents1 = """
class Circle(Shape):
    pass
    """
    file_contents2 = """
class Circle(Shape):
    pass
    """

    _, my_files = create_mock_codebase(
        "my_dir", ("my_file1.py", file_contents1), ("my_file2.py", file_contents2)
    )
    definition_map = parse_definition_nodes_from_codebase(my_files)

    assert len(definition_map) == 1
    assert (
        isinstance(definition_map["Circle"], set) and len(definition_map["Circle"]) == 2
    )


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
from my_package.math.addition import add_two_numbers
from my_package.math.shapes import Square
from my_package.strings import reverse_string, concatenate_strings
    """

    _, my_files = create_mock_codebase("my_dir", ("my_file.py", file_contents))
    imports = parse_import_nodes_from_file(my_files[0], "my_package", definition_map)

    assert len(imports) == 3
    assert all(
        path in imports
        for path in (
            "my_package/math/addition.py",
            "my_package/math/geometry.py",
            "my_package/strings/strings.py",
        )
    )


def test_parse_import_nodes_from_file_with_ambiguous_imports(
    create_mock_codebase: Callable,
) -> None:
    file_contents = """
from my_package.math import add_two_numbers
    """
    _, my_files = create_mock_codebase("my_dir", ("my_file.py", file_contents))

    # Namespace collision means we need to pick the closest import
    definition_map = {
        "add_two_numbers": {"my_package/math/addition.py", "my_package/core/utils.py"},
    }

    imports = parse_import_nodes_from_file(my_files[0], "my_package", definition_map)
    assert len(imports) == 1

    # The import statement included "math" so we pick the first option
    assert "my_package/math/addition.py" in imports
    assert "my_package/core/utils.py" not in imports


def test_parse_import_nodes_from_codebase(
    create_mock_codebase: Callable, definition_map: Dict[str, Set[str]]
) -> None:
    file_contents1 = """
import copy
import datetime
import json
import logging

from my_package.core import Square
from my_package.util import add_two_numbers
    """
    file_contents2 = """
import pandas as pd
import numpy as np
import os

from my_package.math import Triangle
from my_package.strings.strings import reverse_string, concatenate_strings
    """

    _, my_files = create_mock_codebase(
        "my_dir", ("my_file1.py", file_contents1), ("my_file2.py", file_contents2)
    )
    imports = parse_import_nodes_from_codebase(my_files, "my_package", definition_map)
    print(imports)

    assert len(imports) == 3
    keys = [
        "my_package/math/addition.py",
        "my_package/strings/strings.py",
        "my_package/math/geometry.py",
    ]
    assert all(file in imports for file in keys)
    assert len(imports["my_package/math/addition.py"]) == 1
    assert len(imports["my_package/strings/strings.py"]) == 1
    assert len(imports["my_package/math/geometry.py"]) == 2  # Imported in both files


def test_parse_pytest_fixtures_from_file_with_simple_fixtures(
    create_mock_codebase: Callable,
) -> None:
    file_contents = """
@pytest.fixture()
def my_empty_fixture():
    pass

@pytest.fixture(scope="session")
def my_other_empty_fixture():
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
def create_shapes():
    # my_package/math/geometry.py
    square = Square()

    # my_package/math/addition.py
    square.x = add_two_numbers(1, 2)
    square.y = add_two_numbers(3, 4)

    return my_class
    """

    _, my_files = create_mock_codebase("my_dir", ("conftest.py", file_contents))
    fixtures = parse_pytest_fixtures_from_file(my_files[0], definition_map)

    assert len(fixtures) == 1
    assert fixtures["create_shapes"] == {
        "my_package/math/geometry.py",
        "my_package/math/addition.py",
    }


# FIXME(cdkini): This functionality needs to be enabled!

# def test_parse_pytest_fixtures_from_file_with_fixtures_referencing_each_other(
#     create_mock_codebase: Callable,
#     definition_map: Dict[str, Set[str]],
# ) -> None:
#     file_contents = """
# @pytest.fixture()
# def my_fixture1():
#     my_class = Square()
#     add_two_numbers(my_class)
#     return my_class


# @pytest.fixture()
# def my_fixture2(my_fixture1): # This should share 'my_fixture1's dependencies
#     return my_fixture1
#     """

#     _, my_files = create_mock_codebase("my_dir", ("conftest.py", file_contents))
#     imports = parse_pytest_fixtures_from_file(my_files[0], definition_map)

#     assert len(imports) == 2
#     assert imports["my_fixture1"] == {
#         "my_package/math/geometry.py",
#         "my_package/math/addition.py",
#     }
#     assert imports["my_fixture2"] == {
#         "my_package/math/geometry.py",
#         "my_package/math/addition.py",
#     }


def test_parse_pytest_fixtures_from_codebase(
    create_mock_codebase: Callable, definition_map: Dict[str, Set[str]]
) -> None:
    file_contents1 = """
@pytest.fixture
def create_circle():
    return Circle()

@pytest.fixture(scope="function")
def create_triangle():
    return Triangle()
    """
    file_contents2 = """
@pytest.fixture
def set_up_strings():
    return concatenate_strings("hello", "world")
    """

    _, my_files = create_mock_codebase(
        "my_dir", ("conftest.py", file_contents1), ("tests/conftest.py", file_contents2)
    )
    fixtures = parse_pytest_fixtures_from_codebase(my_files, definition_map)

    assert len(fixtures) == 2
    print(fixtures.keys())
    assert all(key in fixtures for key in ("create_triangle", "set_up_strings"))
    assert fixtures["create_triangle"] == {"my_package/math/geometry.py"}
    assert fixtures["set_up_strings"] == {"my_package/strings/strings.py"}


def test_parse_pytest_tests_from_file_with_imports(
    create_mock_codebase: Callable, definition_map: Dict[str, Set[str]]
) -> None:
    test_file_name = "test_shapes.py"
    file_contents = """
from my_package.math.shapes import Square, Triangle

def test_Square():
    assert Square()

def test_Triangle():
    assert Triangle()
    """

    _, my_files = create_mock_codebase("my_dir", (test_file_name, file_contents))
    file_graph = parse_pytest_tests_from_file(
        my_files[0], "my_package", definition_map, fixture_map={}
    )

    assert len(file_graph) == 1
    assert len(file_graph["my_package/math/geometry.py"]) == 1
    assert list(file_graph["my_package/math/geometry.py"])[0].endswith("test_shapes.py")


def test_parse_pytest_tests_from_file_with_fixtures(
    create_mock_codebase: Callable,
    definition_map: Dict[str, Set[str]],
    fixture_map: Dict[str, Set[str]],
) -> None:
    test_file_name = "test_my_class.py"
    file_contents = """
def test_my_classes(create_shapes):
    pass
"""

    _, my_files = create_mock_codebase("my_dir", (test_file_name, file_contents))

    file_graph = parse_pytest_tests_from_file(
        my_files[0], "my_package", definition_map, fixture_map
    )

    assert len(file_graph) == 1
    assert len(file_graph["my_package/math/geometry.py"]) == 1
    assert list(file_graph["my_package/math/geometry.py"])[0].endswith(
        "test_my_class.py"
    )


def test_parse_pytest_tests_from_file_with_imports_and_fixtures(
    create_mock_codebase: Callable,
    definition_map: Dict[str, Set[str]],
    fixture_map: Dict[str, Set[str]],
) -> None:
    test_file_name = "test_my_class.py"
    file_contents = """
from my_package.core import Square
from my_package.util import add_two_numbers


def test_shapes(create_shapes):
    pass
"""

    _, my_files = create_mock_codebase("my_dir", (test_file_name, file_contents))
    file_graph = parse_pytest_tests_from_file(
        my_files[0], "my_package", definition_map, fixture_map
    )

    assert len(file_graph) == 2
    for file in ("my_package/math/geometry.py", "my_package/math/addition.py"):
        assert len(file_graph[file]) == 1
        assert list(file_graph[file])[0].endswith("test_my_class.py")


def test_parse_pytest_tests_from_codebase(
    create_mock_codebase: Callable,
    definition_map: Dict[str, Set[str]],
    fixture_map: Dict[str, Set[str]],
) -> None:
    file_contents1 = """
from my_package.math.shapes import Square
from my_package.math import add_two_numbers

def test_shapes(create_shapes):
    pass
    """
    file_contents2 = """
from my_package.math.addition import add_two_numbers

@pytest.fixture()
def add_nums():
    return add_two_numbers()

def test_math(fake_fixture, add_nums):
    pass
    """

    _, my_files = create_mock_codebase(
        "my_dir", ("test_file1.py", file_contents1), ("test_file2.py", file_contents2)
    )

    tests_dependency_graph = parse_pytest_tests_from_codebase(
        my_files, "my_package", definition_map, fixture_map
    )

    assert len(tests_dependency_graph) == 2
    assert len(tests_dependency_graph["my_package/math/geometry.py"]) == 1
    assert len(tests_dependency_graph["my_package/math/addition.py"]) == 2


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
