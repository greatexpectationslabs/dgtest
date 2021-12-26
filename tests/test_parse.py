import py

from dgtest.parse import parse_definition_nodes, update_dict


def test_parse_definition_nodes_collects_function_definitions(
    tmpdir: py.path.local,
) -> None:
    my_dir = tmpdir.mkdir("my_dir")
    foo = my_dir.join("foo.py")
    bar = my_dir.join("bar.py")

    foo.write(
        """
def my_first_func():
    pass
    """
    )
    bar.write(
        """
def my_second_func(a: int, b: int) -> int:
    return a + b
    """
    )

    definition_map = parse_definition_nodes([foo, bar])

    assert len(definition_map) == 2
    assert (
        isinstance(definition_map["my_first_func"], set)
        and len(definition_map["my_first_func"]) == 1
    )
    assert (
        isinstance(definition_map["my_second_func"], set)
        and len(definition_map["my_second_func"]) == 1
    )


def test_parse_definition_nodes_collects_class_definitions(
    tmpdir: py.path.local,
) -> None:
    my_dir = tmpdir.mkdir("my_dir")
    foo = my_dir.join("foo.py")
    bar = my_dir.join("bar.py")

    foo.write(
        """
class Foo:
    pass
    """
    )
    bar.write(
        """
class Bar:
    def __init__(self, a: int, b: int):
        self.a = a
        self.b = b
    """
    )

    definition_map = parse_definition_nodes([foo, bar])

    assert len(definition_map) == 2
    assert isinstance(definition_map["Foo"], set) and len(definition_map["Bar"]) == 1
    assert isinstance(definition_map["Bar"], set) and len(definition_map["Bar"]) == 1


def test_parse_definition_nodes_accounts_for_namespace_collision(
    tmpdir: py.path.local,
) -> None:
    my_dir = tmpdir.mkdir("my_dir")
    foo = my_dir.join("foo.py")
    foo.write(
        """
class Foo:
    pass
    """
    )
    bar = my_dir.join("bar.py")
    bar.write(
        """
class Foo:
    def __init__(self, a: int, b: int):
        self.a = a
        self.b = b
    """
    )

    definition_map = parse_definition_nodes([foo, bar])

    assert len(definition_map) == 1
    assert isinstance(definition_map["Foo"], set) and len(definition_map["Foo"]) == 2


def test_update_dict_updates_existing_keys() -> None:
    A = {"foo": {"a", "b", "c"}}
    B = {"foo": {"c", "d", "e"}}

    update_dict(A, B)

    assert len(A) == 1
    assert all(num in A["foo"] for num in ("a", "b", "c", "d", "e"))


def test_update_dict_adds_new_keys() -> None:
    A = {"foo": {"a", "b", "c"}}
    B = {"foo": {"c", "d", "e"}}

    update_dict(A, B)

    assert len(A) == 2
    assert all(num in A["foo"] for num in ("a", "b", "c"))
    assert all(num in A["bar"] for num in ("c", "d", "e"))
