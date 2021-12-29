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
def remove_temp_dir_path_prefix(temporary_directory: Any) -> Callable:
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
def clean_graph(remove_temp_dir_path_prefix: Callable) -> Callable:
    """
    Cleans a given dependency graph to make it more human-readable. The output
    should resemble what a user would see if they ran dgtest in the root of
    the great_expectations repo.
    """

    def _clean_graph(graph: Dict[str, Set[str]]) -> Dict[str, Set[str]]:
        cleaned_graph = {}
        for key, value in graph.items():
            cleaned_key = remove_temp_dir_path_prefix(key)
            cleaned_value = {remove_temp_dir_path_prefix(v) for v in value}
            cleaned_graph[cleaned_key] = cleaned_value
        return cleaned_graph

    return _clean_graph


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


def test_great_expectations_parsing(great_expectations: Tuple[str, str]) -> None:
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

    classes_with_namspace_collisions = [
        "BaseUpgradeHelper",
        "BatchMarkers",
        "DatasourceTypes",
        "Email",
        "Mark",
        "MetaPandasDataset",
        "Profiler",
        "SuiteEditNotebookRenderer",
        "SupportedDatabases",
        "UpgradeHelperV11",
        "UpgradeHelperV13",
        "Validator",
    ]
    assert all(
        len(definition_map[class_]) > 1 for class_ in classes_with_namspace_collisions
    )

    funcs_with_namespace_collisions = [
        "build_docs",
        "checkpoint",
        "checkpoint_list",
        "checkpoint_new",
        "checkpoint_run",
        "checkpoint_script",
        "cli",
        "cli_colorize_string",
        "cli_message",
        "cli_message_dict",
        "cli_message_list",
        "datasource",
        "datasource_list",
        "datasource_new",
        "delete_checkpoint",
        "delete_datasource",
        "docs",
        "docs_build",
        "docs_list",
        "init",
        "load_checkpoint",
        "load_data_context_with_error_handling",
        "load_expectation_suite",
        "main",
        "parse_result_format",
        "run_checkpoint",
        "select_datasource",
        "send_usage_message",
        "store",
        "store_list",
        "suite",
        "suite_delete",
        "suite_demo",
        "suite_edit",
        "suite_list",
        "suite_new",
    ]
    assert all(
        len(definition_map[func]) > 1 for func in funcs_with_namespace_collisions
    )

    # 3. Parse all import statements in source files to create a dependency graph ======================================

    dependency_graph = parse_import_nodes_from_codebase(
        source_files, "great_expectations", definition_map
    )
    assert len(dependency_graph) == 194

    # Selecting sqlalchemy_batch_data.py an an example of proper dependency linking
    standard_node = os.path.join(source, "execution_engine/sqlalchemy_batch_data.py")
    assert dependency_graph[standard_node] == {
        os.path.join(source, "execution_engine/sqlalchemy_execution_engine.py"),
        os.path.join(
            source, "expectations/metrics/table_metrics/table_column_types.py"
        ),
        os.path.join(source, "self_check/util.py"),
    }

    # 4. Parse all pytest fixtures in conftests ========================================================================

    fixture_map = parse_pytest_fixtures_from_codebase(test_files, definition_map)

    assert len(fixture_map) == 116
    assert len(fixture_map["spark_session"]) == 2
    assert all(
        os.path.join(source, source_file) in fixture_map["spark_session"]
        for source_file in ("core/util.py", "dataset/sparkdf_dataset.py")
    )

    # 5. Parse all pytest tests in test files ==========================================================================

    tests_dependency_graph = parse_pytest_tests_from_codebase(
        test_files, "great_expectations", definition_map, fixture_map
    )

    assert len(tests_dependency_graph) == 163
    for test_sets in tests_dependency_graph.values():
        assert all(Path(file).stem.startswith("test_") for file in test_sets)

    usage_statistics_path = os.path.join(
        source, "core/usage_statistics/usage_statistics.py"
    )
    usage_statistics_tests = tests_dependency_graph[usage_statistics_path]
    assert len(usage_statistics_tests) == 4
    assert all(
        Path(test_file).stem
        in (
            "test_usage_statistics",
            "test_usage_statistics_handler_methods",
            "test_util",
            "test_expectation_arguments",
        )
        for test_file in usage_statistics_tests
    )


def test_great_expectations_dependency_graphs(
    great_expectations: Tuple[str, str], snapshot: Any, clean_graph: Callable
) -> None:
    source, tests = great_expectations
    source_dependency_graph, tests_dependency_graph = get_dependency_graphs(
        source, tests
    )

    assert len(source_dependency_graph) == 194
    cleaned_source_dependency_graph = clean_graph(source_dependency_graph)
    snapshot.assert_match(cleaned_source_dependency_graph)

    assert len(tests_dependency_graph) == 163
    cleaned_tests_dependency_graph = clean_graph(tests_dependency_graph)
    snapshot.assert_match(cleaned_tests_dependency_graph)


def test_great_expectations_determine_tests_to_run_depth(
    great_expectations: Tuple[str, str], snapshot: Any, clean_graph: Callable
) -> None:
    source, tests = great_expectations
    source_dependency_graph, tests_dependency_graph = get_dependency_graphs(
        source, tests
    )

    files_to_test = {}
    for source_file in source_dependency_graph:
        relevant_tests = determine_tests_to_run(
            [source_file],
            [],
            source_dependency_graph,
            tests_dependency_graph,
            depth=2,
            ignore_paths=[],
            filter_=None,
        )
        files_to_test[source_file] = relevant_tests

    cleaned_files_to_test = clean_graph(files_to_test)
    snapshot.assert_match(cleaned_files_to_test)
