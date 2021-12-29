import os
from pathlib import Path
from typing import Any, Callable, Dict, Set, Tuple

import git
import pytest

from dgtest.fs import retrieve_all_source_files, retrieve_all_test_files
from dgtest.graph import determine_tests_to_run
from dgtest.parse import (
    get_dependency_graphs,
    parse_definition_nodes_from_codebase,
    parse_import_nodes_from_codebase,
    parse_pytest_fixtures_from_codebase,
    parse_pytest_tests_from_codebase,
)


@pytest.fixture(scope="session")
def temporary_directory(tmpdir_factory: Any) -> Any:
    directory = tmpdir_factory.mktemp("tmp")
    return directory


@pytest.fixture(scope="session")
def remove_tmpdir_path_prefix(temporary_directory: Any) -> Callable:
    """
    Since tmpdir and tmpdir_factory create really long path prefixes, this utility
    cleans strings to be more human-readable.
    """
    temp_dir_path = temporary_directory.strpath

    def _remove_temp_dir_path_prefix(path: str) -> str:
        p = Path(str(os.path.relpath(path, temp_dir_path)))
        return "/".join(part for part in p.parts[1:])

    return _remove_temp_dir_path_prefix


@pytest.fixture(scope="session")
def clean_dictionary_of_tmpdir_prefix(remove_tmpdir_path_prefix: Callable) -> Callable:
    """
    Cleans a given dependency graph to make it more human-readable. The output
    should resemble what a user would see if they ran dgtest in the root of
    the great_expectations repo.
    """

    def _clean_dictionary_of_tmpdir_prefix(
        graph: Dict[str, Set[str]]
    ) -> Dict[str, Set[str]]:
        cleaned_graph = {}
        for key, value in graph.items():
            cleaned_key = remove_tmpdir_path_prefix(key)
            cleaned_value = {remove_tmpdir_path_prefix(v) for v in value}
            cleaned_graph[cleaned_key] = cleaned_value
        return cleaned_graph

    return _clean_dictionary_of_tmpdir_prefix


@pytest.fixture(scope="session")
def great_expectations(temporary_directory: Any) -> Tuple[str, str]:
    """
    Clone GE v0.13.49 into a temporary directory so we can run our integration tests
    on a real example.

    TODO: Improve performance!
    """
    directory = temporary_directory
    destination = directory.mkdir("great_expectations").strpath
    repo = git.Repo.clone_from(
        "https://github.com/great-expectations/great_expectations",
        destination,
        single_branch=True,
        branch="main",
        depth=1,
    )

    # Pinning to a particular release to be consistent between runs
    repo.git.checkout("0.13.49")

    source = os.path.join(destination, "great_expectations")
    tests = os.path.join(destination, "tests")
    return source, tests


def test_great_expectations_parsing(
    great_expectations: Tuple[str, str],
    clean_dictionary_of_tmpdir_prefix: Callable,
    snapshot: Any,
) -> None:
    # 1. Gather all source/test files from the GE repo for later use ===================================================

    source, tests = great_expectations

    source_files = retrieve_all_source_files(source)
    test_files = retrieve_all_test_files(source, tests)

    assert len(source_files) == 416
    assert len(test_files) == 241

    conftests = [file for file in test_files if file.endswith("conftest.py")]
    assert len(conftests) == 8

    # 2. Create a map between all function/class definitions and where they originate ==================================

    definition_map = parse_definition_nodes_from_codebase(source_files)
    assert len(definition_map) == 1099
    cleaned_definition_map = clean_dictionary_of_tmpdir_prefix(definition_map)
    snapshot.assert_match(cleaned_definition_map)

    # 3. Parse all import statements in source files to create a dependency graph ======================================

    dependency_graph = parse_import_nodes_from_codebase(
        source_files, "great_expectations", definition_map
    )
    assert len(dependency_graph) == 194
    cleaned_dependency_graph = clean_dictionary_of_tmpdir_prefix(dependency_graph)
    snapshot.assert_match(cleaned_dependency_graph)

    # 4. Parse all pytest fixtures in conftests ========================================================================

    fixture_map = parse_pytest_fixtures_from_codebase(test_files, definition_map)

    assert len(fixture_map) == 116
    cleaned_fixture_map = clean_dictionary_of_tmpdir_prefix(fixture_map)
    snapshot.assert_match(cleaned_fixture_map)

    # 5. Parse all pytest tests in test files ==========================================================================

    tests_dependency_graph = parse_pytest_tests_from_codebase(
        test_files, "great_expectations", definition_map, fixture_map
    )

    assert len(tests_dependency_graph) == 163
    cleaned_tests_dependency_graph = clean_dictionary_of_tmpdir_prefix(
        tests_dependency_graph
    )
    snapshot.assert_match(cleaned_tests_dependency_graph)


def test_great_expectations_determine_tests_to_run_depth(
    great_expectations: Tuple[str, str],
    snapshot: Any,
    clean_dictionary_of_tmpdir_prefix: Callable,
) -> None:
    source, tests = great_expectations
    source_dependency_graph, tests_dependency_graph = get_dependency_graphs(
        source, tests
    )

    # Clean dependency graphs to remove any tmpdir prefixes
    cleaned_source_dependency_graph = clean_dictionary_of_tmpdir_prefix(
        source_dependency_graph
    )
    cleaned_tests_dependency_graph = clean_dictionary_of_tmpdir_prefix(
        tests_dependency_graph
    )

    # Create a mock commit (these are the files we identify through our git diff)
    changed_source_files = [
        "great_expectations/render/renderer/microsoft_teams_renderer.py",
        "great_expectations/data_asset/data_asset.py",
        "great_expectations/rule_based_profiler/rule/rule.py",
    ]
    changed_test_files = [
        "tests/datasource/data_connector/test_inferred_asset_dbfs_data_connector.py",
        "tests/execution_engine/test_sparkdf_execution_engine.py",
        "tests/data_context/store/test_configuration_store.py",
    ]

    # Pretend each file is a separate change or commit and see what the output is
    relevant_tests = determine_tests_to_run(
        changed_source_files,
        changed_test_files,
        cleaned_source_dependency_graph,
        cleaned_tests_dependency_graph,
        depth=2,
        ignore_paths=[],
        filter_=None,
    )

    assert len(relevant_tests) == 146
    snapshot.assert_match(relevant_tests)
