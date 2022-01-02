from dgtest.core.graph import (
    determine_relevant_source_files,
    determine_test_candidates,
    filter_test_candidates,
)


def test_determine_relevant_source_file_to_run() -> None:
    graph = {
        "my_source/A": {"my_source/C"},
        "my_source/B": {"my_source/A", "my_source/D"},
        "my_source/C": {"my_source/B", "not_my_source/F"},
        "my_source/D": {"my_source/C"},
        "my_source/E": {"my_source/C", "my_source/A"},
    }

    res = determine_relevant_source_files(graph, ["my_source/A"], depth=2)
    assert len(res) == 2
    assert all(node in res for node in ("my_source/A", "my_source/C"))


def test_determine_test_candidates_without_changed_test_files() -> None:
    tests_dependency_graph = {
        "source1": {"my_test1", "my_test2"},
        "source2": {"my_test1"},
        "source3": {"my_test1", "my_test3"},
        "source4": {"my_test4", "my_test5", "my_test6"},
        "source5": {"my_test1", "my_test3"},
    }
    source_files = ["source1", "source2", "source3"]

    candidates = determine_test_candidates(tests_dependency_graph, source_files, [])
    assert candidates == ["my_test1", "my_test2", "my_test3"]


def test_determine_test_candidates_with_changed_test_files() -> None:
    tests_dependency_graph = {
        "source1": {"my_test1", "my_test2"},
        "source2": {"my_test1"},
        "source3": {"my_test1", "my_test3"},
        "source4": {"my_test4", "my_test5", "my_test6"},
        "source5": {"my_test1", "my_test3"},
    }
    source_files = ["source1", "source2", "source3"]
    changed_test_files = ["my_test4", "my_test5"]

    candidates = determine_test_candidates(
        tests_dependency_graph, source_files, changed_test_files
    )
    assert candidates == ["my_test1", "my_test2", "my_test3", "my_test4", "my_test5"]


def test_filter_test_candidates_with_ignore_paths() -> None:
    candidates = [
        "a/b/c",
        "a/b/d",
        "a/c/e",
        "a/c/f",
        "b/d/e",
    ]
    ignore_paths = ["b", "a/c"]

    tests = filter_test_candidates(candidates, ignore_paths, filter_=None)
    assert tests == ["a/b/c", "a/b/d"]


def test_filter_test_candidates_with_filter() -> None:
    candidates = [
        "a/b/c",
        "a/b/d",
        "a/c/e",
        "a/c/f",
        "b/d/e",
    ]

    tests = filter_test_candidates(candidates, [], filter_="a/c")
    assert tests == ["a/c/e", "a/c/f"]


def test_filter_test_candidates_with_ignore_paths_and_filter() -> None:
    candidates = [
        "a/b/c",
        "a/b/d",
        "a/c/e",
        "a/c/f",
        "b/d/e",
    ]
    ignore_paths = ["b", "a/c"]

    tests = filter_test_candidates(candidates, ignore_paths, filter_="a/b/c")
    assert tests == ["a/b/c"]
