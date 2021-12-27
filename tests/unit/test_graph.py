from dgtest.graph import traverse_graph


def test_traverse_graph() -> None:
    graph = {
        "my_source/A": {"my_source/C"},
        "my_source/B": {"my_source/A", "my_source/D"},
        "my_source/C": {"my_source/B"},
        "my_source/D": {"my_source/C"},
        "my_source/E": {"my_source/C", "my_source/A"},
    }

    res = traverse_graph("my_source/A", "my_source", graph, depth=2)
    assert len(res) == 2
    assert all(node in res for node in ("my_source/A", "my_source/C"))
