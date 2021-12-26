import ast
import difflib
from collections import defaultdict, namedtuple
from typing import DefaultDict, Dict, List, Optional, Set

Import = namedtuple("Import", ["source", "module", "name", "alias"])


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

        for n in node.names:  # type: ignore [attr-defined] - mypy doesn't agree with Union[ast.Import, ast.ImportFrom] having a names attr
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
        closest = difflib.get_close_matches(partial_path, candidates)[0]
        return str(closest)


def update_dict(A: Dict[str, Set[str]], B: Dict[str, Set[str]]) -> None:
    for key, val in A.items():
        if key in B:
            A[key] = val.union(B[key])

    for key, val in B.items():
        if key not in A:
            A[key] = set(v for v in val)
