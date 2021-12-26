import ast
from collections import defaultdict
from typing import DefaultDict, Dict, List, Set


def parse_definition_nodes(files: List[str]) -> DefaultDict[str, Set[str]]:
    definition_map: DefaultDict[str, Set[str]] = defaultdict(set)
    for file in files:
        file_definition_map = _parse_definition_nodes(file)
        update_dict(definition_map, file_definition_map)
    return definition_map


def _parse_definition_nodes(file: str) -> DefaultDict[str, Set[str]]:
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


def update_dict(A: Dict[str, Set[str]], B: Dict[str, Set[str]]) -> None:
    for key, val in A.items():
        if key in B:
            A[key] = val.union(B[key])

    for key, val in B.items():
        if key not in A:
            A[key] = set(v for v in val)
