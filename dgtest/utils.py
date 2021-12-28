import glob
import logging
import pathlib
from typing import List, Optional, Tuple

import git

logger = logging.getLogger(__name__)


def get_changed_files(branch: str) -> Tuple[List[str], List[str]]:
    repo = git.Repo()
    diff = repo.git.diff(branch, name_only=True)
    files = [f.strip() for f in diff.split("\n")]
    changed_source_files = _filter_source_files(files)
    changed_test_files = _filter_test_files(files)
    return changed_source_files, changed_test_files


def retrieve_all_source_files(source: str) -> List[str]:
    all_files = _retrieve_all_py_files(source)
    source_files = _filter_source_files(all_files)
    return source_files


def retrieve_all_test_files(source: str, tests: Optional[str] = None) -> List[str]:
    all_files = _retrieve_all_py_files(source)
    if tests is not None:
        path = pathlib.Path(tests)
        if not path.exists():
            logger.warn(f"Test directory '{tests}' was not found; skipping analysis")
        else:
            all_files += _retrieve_all_py_files(tests)

    test_files = _filter_test_files(all_files)
    return test_files


def _retrieve_all_py_files(directory: str) -> List[str]:
    return [file for file in glob.glob(f"{directory}/**/*.py", recursive=True)]


def _filter_source_files(files: List[str]) -> List[str]:
    source_files = []
    for file in files:
        path = pathlib.Path(file)
        if not _is_existing_py_file(path):
            continue
        stem = path.stem
        if not (stem == "conftest" or path.stem.startswith("test_")):
            source_files.append(str(path))
    return source_files


def _filter_test_files(files: List[str]) -> List[str]:
    test_files = []
    for file in files:
        path = pathlib.Path(file)
        if not _is_existing_py_file(path):
            continue
        stem = path.stem
        if stem == "conftest" or stem.startswith("test_"):
            test_files.append(str(path))
    return test_files


def _is_existing_py_file(path: pathlib.Path) -> bool:
    return path.is_file() and path.suffix == ".py"
