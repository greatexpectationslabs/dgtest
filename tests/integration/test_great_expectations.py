import os
from pathlib import Path
from typing import Any, Tuple

import git
import pytest

from dgtest.parse import (
    parse_definition_nodes_from_codebase,
    parse_import_nodes_from_codebase,
    parse_pytest_fixtures_from_codebase,
    parse_pytest_tests_from_codebase,
)
from dgtest.utils import retrieve_all_source_files, retrieve_all_test_files


@pytest.fixture(scope="session")
def pinned_release() -> str:
    # Release 0.13.49 - https://github.com/great-expectations/great_expectations/commit/a1f42adeb54902d696a8ac73a20ae6f7c39ad16f
    return "a1f42adeb54902d696a8ac73a20ae6f7c39ad16f"


@pytest.fixture(scope="session")
def great_expectations(tmpdir_factory: Any, pinned_release: str) -> Tuple[str, str]:
    directory = tmpdir_factory.mktemp("tmp")
    destination = directory.mkdir("great_expectations").strpath
    repo = git.Repo.clone_from(
        "https://github.com/great-expectations/great_expectations",
        destination,
        no_checkout=True,
        depth=1,
    )
    repo.git.checkout(pinned_release)

    source = os.path.join(destination, "great_expectations")
    tests = os.path.join(destination, "tests")
    return source, tests


def test_great_expectations(great_expectations: Tuple[str, str]) -> None:
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
    assert len(dependency_graph) == 416

    # Selecting registry.py an an example of proper dependency linking
    standard_node = os.path.join(source, "expectations/registry.py")
    assert dependency_graph[standard_node] == {
        os.path.join(source, "core/id_dict.py"),
        os.path.join(source, "core/metric.py"),
        os.path.join(source, "validator/metric_configuration.py"),
    }

    # No file relies on the functions/classes defined in exceptions.py
    orphaned_node = os.path.join(source, "render/exceptions.py")
    assert dependency_graph[orphaned_node] == set()

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
