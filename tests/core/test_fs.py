from typing import Callable, List, Tuple
from unittest import mock

import py
import pytest

from dgtest.core.fs import (
    get_changed_files,
    retrieve_all_source_files,
    retrieve_all_test_files,
)


@pytest.fixture(scope="function")
def create_mock_files(tmpdir: py.path.local) -> Callable:
    def _create_mock_files(directory: str, *files: str) -> Tuple[str, List[str]]:
        my_dir = tmpdir.mkdir(directory)
        my_files = []
        for name in files:
            temp_file = my_dir.join(name)
            temp_file.write("")
            my_files.append(temp_file.strpath)
        return my_dir.strpath, my_files

    return _create_mock_files


def test_get_changed_files_only_source_files(create_mock_files: Callable) -> None:
    _, files = create_mock_files("my_dir", "foo.py", "bar.py", "baz.py")
    with mock.patch("dgtest.core.fs.git.Repo") as mock_repo:
        mock_repo().git.diff.return_value = "\n".join(file for file in files)
        changed_source_files, changed_test_files = get_changed_files("origin/master")

    assert len(changed_source_files) == 3
    assert len(changed_test_files) == 0


def test_get_changed_files_both_source_and_test_files(
    create_mock_files: Callable,
) -> None:
    _, files = create_mock_files(
        "my_dir",
        "foo.py",
        "bar.py",
        "baz.py",
        "test_foo.py",
        "test_bar.py",
        "test_baz.py",
        "conftest.py",
    )
    with mock.patch("dgtest.core.fs.git.Repo") as mock_repo:
        mock_repo().git.diff.return_value = "\n".join(file for file in files)
        changed_source_files, changed_test_files = get_changed_files("origin/master")

    assert len(changed_source_files) == 3
    assert len(changed_test_files) == 4


def test_get_changed_files_excludes_non_py_files(
    create_mock_files: Callable,
) -> None:
    _, files = create_mock_files(
        "my_dir", "foo.yml", "bar.json", "README.md", "LICENSE"
    )
    with mock.patch("dgtest.core.fs.git.Repo") as mock_repo:
        mock_repo().git.diff.return_value = "\n".join(file for file in files)
        changed_source_files, changed_test_files = get_changed_files("origin/master")

    assert len(changed_source_files) == 0
    assert len(changed_test_files) == 0


def test_get_changed_files_excludes_nonexistant_files(tmpdir: py.path.local) -> None:
    my_dir = tmpdir.mkdir("my_dir")
    fake_file = my_dir.join("fake_file.py")

    with mock.patch("dgtest.core.fs.git.Repo") as mock_repo:
        mock_repo().git.diff.return_value = fake_file.strpath
        changed_source_files, changed_test_files = get_changed_files("origin/master")

    assert len(changed_source_files) == 0
    assert len(changed_test_files) == 0


def test_retrieve_all_source_files(create_mock_files: Callable) -> None:
    my_dir, _ = create_mock_files(
        "my_dir", "foo.py", "bar.py", "test_foo.py", "test_bar.py"
    )
    source_files = retrieve_all_source_files(my_dir)
    assert len(source_files) == 2


def test_retrieve_all_test_files_without_test_arg(
    create_mock_files: Callable,
) -> None:
    my_source_dir, _ = create_mock_files(
        "my_dir", "foo.py", "bar.py", "test_foo.py", "test_bar.py"
    )
    my_test_dir = None
    test_files = retrieve_all_test_files(my_source_dir, my_test_dir)
    assert len(test_files) == 2


def test_retrieve_all_test_files_with_test_arg(create_mock_files: Callable) -> None:
    my_source_dir, _ = create_mock_files(
        "my_dir", "foo.py", "bar.py", "test_foo.py", "test_bar.py"
    )
    my_test_dir, _ = create_mock_files("tests", "test_baz.py", "test_qux.py")
    test_files = retrieve_all_test_files(my_source_dir, my_test_dir)
    assert len(test_files) == 4
