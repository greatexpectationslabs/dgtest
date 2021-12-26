import pathlib
from typing import List, Tuple

import git


def get_changed_files(source: str, branch: str) -> Tuple[List[str], List[str]]:
    repo = git.Repo()
    diff = repo.git.diff(branch, name_only=True)
    files = [f.strip() for f in diff.split("\n")]
    changed_source_files = _get_changed_source_files(files, source)
    changed_test_files = _get_changed_test_files(files)
    return changed_source_files, changed_test_files


def _get_changed_source_files(files: List[str], source: str) -> List[str]:
    source_files = []
    for file in files:
        path = pathlib.Path(file)
        if (
            not _is_existing_py_file(path)
            or path.stem.startswith("test_")
            or not str(path.parent).startswith(source)
        ):
            continue
        source_files.append(str(path))
    return source_files


def _get_changed_test_files(files: List[str]) -> List[str]:
    test_files = []
    for file in files:
        path = pathlib.Path(file)
        if not _is_existing_py_file(path) or not path.stem.startswith("test_"):
            continue
        test_files.append(str(path))
    return test_files


def _is_existing_py_file(path: pathlib.Path) -> bool:
    return path.is_file() and path.suffix == ".py"
