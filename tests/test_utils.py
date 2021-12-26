from unittest import mock

import py

from dgtest.utils import get_changed_files


def test_get_changed_files_only_source_files(tmpdir: py.path.local) -> None:
    my_dir = tmpdir.mkdir("my_dir")
    files = []
    for name in ("foo.py", "bar.py", "baz.py"):
        temp_file = my_dir.join(name)
        temp_file.write("")
        files.append(temp_file.strpath)

    with mock.patch("dgtest.utils.git.Repo") as mock_repo:
        mock_repo().git.diff.return_value = "\n".join(file for file in files)
        changed_source_files, changed_test_files = get_changed_files(
            my_dir.strpath, "origin/master"
        )

    assert len(changed_source_files) == 3
    assert len(changed_test_files) == 0


def test_get_changed_files_both_source_and_test_files(tmpdir: py.path.local) -> None:
    my_dir = tmpdir.mkdir("my_dir")
    files = []
    for name in (
        "foo.py",
        "bar.py",
        "baz.py",
        "test_foo.py",
        "test_bar.py",
        "test_baz.py",
    ):
        temp_file = my_dir.join(name)
        temp_file.write("")
        files.append(temp_file.strpath)

    with mock.patch("dgtest.utils.git.Repo") as mock_repo:
        mock_repo().git.diff.return_value = "\n".join(file for file in files)
        changed_source_files, changed_test_files = get_changed_files(
            my_dir.strpath, "origin/master"
        )

    assert len(changed_source_files) == 3
    assert len(changed_test_files) == 3


def test_get_changed_files_excludes_non_py_files(tmpdir: py.path.local) -> None:
    my_dir = tmpdir.mkdir("my_dir")
    files = []
    for name in (
        "foo.yml",
        "bar.json",
        "README.md",
        "LICENSE",
    ):
        temp_file = my_dir.join(name)
        temp_file.write("")
        files.append(temp_file.strpath)

    with mock.patch("dgtest.utils.git.Repo") as mock_repo:
        mock_repo().git.diff.return_value = "\n".join(file for file in files)
        changed_source_files, changed_test_files = get_changed_files(
            my_dir.strpath, "origin/master"
        )

    assert len(changed_source_files) == 0
    assert len(changed_test_files) == 0


def test_get_changed_files_excludes_nonexistant_files(tmpdir: py.path.local) -> None:
    my_dir = tmpdir.mkdir("my_dir")
    fake_file = my_dir.join("fake_file.py")

    with mock.patch("dgtest.utils.git.Repo") as mock_repo:
        mock_repo().git.diff.return_value = fake_file.strpath
        changed_source_files, changed_test_files = get_changed_files(
            my_dir.strpath, "origin/master"
        )

    assert len(changed_source_files) == 0
    assert len(changed_test_files) == 0
