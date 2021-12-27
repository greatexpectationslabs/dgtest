import ast
import difflib
import pathlib
from collections import defaultdict, namedtuple
from typing import DefaultDict, Dict, List, Optional, Set, Tuple

from dgtest.utils import retrieve_all_source_files, retrieve_all_test_files

Import = namedtuple("Import", ["source", "module", "name", "alias"])


def get_dependency_graphs(
    source: str, tests: str
) -> Tuple[Dict[str, Set[str]], Dict[str, Set[str]]]:
    # Identify relevant files for later steps
    source_files = retrieve_all_source_files(source)
    test_files = retrieve_all_test_files(tests)

    # Parse function/class defs and fixtures
    definition_map = parse_definition_nodes_from_codebase(source_files)
    fixture_map = parse_pytest_fixtures_from_codebase(test_files, definition_map)

    # Use prior steps to generate relevant dependency graphs
    source_dependency_graph = parse_import_nodes_from_codebase(
        source_files, source, definition_map
    )
    tests_dependency_graph = parse_pytest_tests_from_codebase(
        test_files, source, definition_map, fixture_map
    )

    return source_dependency_graph, tests_dependency_graph


# Parse function/class definitions =====================================================================================


def parse_definition_nodes_from_codebase(files: List[str]) -> Dict[str, Set[str]]:
    definition_map: Dict[str, Set[str]] = {}
    for file in files:
        file_definition_map = parse_definition_nodes_from_file(file)
        update_dict(definition_map, file_definition_map)
    return definition_map


def parse_definition_nodes_from_file(file: str) -> DefaultDict[str, Set[str]]:
    with open(file) as f:
        root = ast.parse(f.read(), file)

    definition_nodes = []
    for node in root.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            definition_nodes.append(node.name)

    file_definition_map: DefaultDict[str, Set[str]] = defaultdict(set)
    for name in definition_nodes:
        file_definition_map[name].add(file)

    return file_definition_map


# Parse import statements ==============================================================================================


def parse_import_nodes_from_codebase(
    files: List[str], source: str, definition_map: Dict[str, Set[str]]
) -> Dict[str, Set[str]]:
    imports: Dict[str, Set[str]] = {}
    for file in files:
        file_imports = parse_import_nodes_from_file(file, source, definition_map)
        imports[file] = file_imports
    return imports


def parse_import_nodes_from_file(
    file: str,
    source: str,
    definition_map: Dict[str, Set[str]],
) -> Set[str]:
    imports = _gather_import_nodes_from_file(file)
    paths = set()
    for import_ in imports:
        path = _generate_path_from_import_node(import_, source, definition_map)
        if path is not None:
            paths.add(path)

    return paths


def _gather_import_nodes_from_file(file: str) -> List[Import]:
    with open(file) as f:
        root = ast.parse(f.read(), file)

    imports = []
    for node in root.body:
        if isinstance(node, ast.Import):
            module: List[str] = []
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            module = node.module.split(".")
        else:
            continue

        for n in node.names:  # type: ignore [attr-defined] - mypy doesn't agree with Union[ast.Import, ast.ImportFrom] having a 'names' attr
            import_ = Import(file, module, n.name.split("."), n.asname)
            imports.append(import_)

    return imports


def _generate_path_from_import_node(
    import_: Import, source: str, definition_map: Dict[str, Set[str]]
) -> Optional[str]:
    partial_path = "/".join(m for m in import_.module)
    if not import_.module or not import_.name or not partial_path.startswith(source):
        return None
    key = import_.name[0]
    candidates: Set[str] = definition_map.get(key, set())
    if len(candidates) == 0:
        return None
    elif len(candidates) == 1:
        return list(candidates)[0]
    else:
        # If we're not sure of the origin, use the stringified import statement and make an educated guess
        closest = difflib.get_close_matches(partial_path, candidates, n=1, cutoff=0)
        return str(closest[0])


# Parse pytest fixtures ================================================================================================


def parse_pytest_fixtures_from_codebase(
    test_files: List[str], definition_map: Dict[str, Set[str]]
) -> Dict[str, Set[str]]:
    fixture_map: Dict[str, Set[str]] = {}
    for file in test_files:
        path = pathlib.Path(file)
        if path.stem == "conftest":
            file_fixtures = parse_pytest_fixtures_from_file(file, definition_map)
            update_dict(fixture_map, file_fixtures)
    return fixture_map


def parse_pytest_fixtures_from_file(
    file: str, definition_map: Dict[str, Set[str]]
) -> Dict[str, Set[str]]:
    fixture_nodes = _gather_fixture_nodes_from_file(file)

    # Parse the body of each fixture and find symbols.
    # If that symbol is something that was defined in the source files (class or function),
    # create an association between the fixture and the file that the symbol was declared in.
    fixture_map: DefaultDict[str, Set[str]] = defaultdict(set)
    for node in fixture_nodes:
        _create_associations_between_fixture_and_definitions(
            node, fixture_map, definition_map
        )

    return fixture_map


def _gather_fixture_nodes_from_file(file: str) -> List[ast.FunctionDef]:
    with open(file) as f:
        root = ast.parse(f.read(), file)

    fixture_nodes = []
    for node in root.body:
        if isinstance(node, ast.FunctionDef):
            for d in node.decorator_list:
                if isinstance(d, ast.Attribute) and d.attr == "fixture":
                    fixture_nodes.append(node)
                elif (
                    isinstance(d, ast.Call)
                    and hasattr(d.func, "attr")
                    and d.func.attr == "fixture"  # type: ignore [attr-defined] - mypy doesn't love this 'attr' attr
                ):
                    fixture_nodes.append(node)

    return fixture_nodes


def _create_associations_between_fixture_and_definitions(
    fixture_node: ast.FunctionDef,
    fixture_map: DefaultDict[str, Set[str]],
    definition_map: Dict[str, Set[str]],
) -> None:
    for child in ast.walk(fixture_node):
        for symbol in child.__dict__.values():
            if isinstance(symbol, str) and symbol in definition_map:
                candidates = definition_map[symbol]
                for candidate in candidates:
                    fixture_map[fixture_node.name].add(candidate)


# Parse pytest tests ===================================================================================================


def parse_pytest_tests_from_codebase(
    test_files: List[str],
    source: str,
    definition_map: Dict[str, Set[str]],
    fixture_map: Dict[str, Set[str]],
) -> Dict[str, Set[str]]:
    tests_dependency_graph: Dict[str, Set[str]] = {}
    for file in test_files:
        path = pathlib.Path(file)
        if path.stem.startswith("test_"):
            file_graph = parse_pytest_tests_from_file(
                file, source, definition_map, fixture_map
            )
            update_dict(tests_dependency_graph, file_graph)

    return tests_dependency_graph


def parse_pytest_tests_from_file(
    test_file: str,
    source: str,
    definition_map: Dict[str, Set[str]],
    fixture_map: Dict[str, Set[str]],
) -> DefaultDict[str, Set[str]]:
    # Parse the test file's imports and create associations between source files and test files
    file_graph: DefaultDict[str, Set[str]] = defaultdict(set)
    source_file_paths = parse_import_nodes_from_file(test_file, source, definition_map)
    for source_file in source_file_paths:
        file_graph[source_file].add(test_file)

    with open(test_file) as f:
        root = ast.parse(f.read(), test_file)

    # For each test function declaration in the test file, check the args to see if they are fixtures
    # If they are, add the fixture's dependencies
    for node in root.body:
        if isinstance(node, ast.FunctionDef):
            for symbol in node.args.args:
                arg = symbol.arg
                for source_file in fixture_map.get(arg, set()):
                    file_graph[source_file].add(test_file)

    return file_graph


# Miscellaneous ========================================================================================================


def update_dict(A: Dict[str, Set[str]], B: Dict[str, Set[str]]) -> None:
    for key, val in A.items():
        if key in B:
            A[key] = val.union(B[key])

    for key, val in B.items():
        if key not in A:
            A[key] = set(v for v in val)
