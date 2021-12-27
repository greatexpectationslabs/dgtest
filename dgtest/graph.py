from typing import Dict, Set


def traverse_graph(
    root: str, source: str, graph: Dict[str, Set[str]], depth: int
) -> Set[str]:
    stack = [(root, depth)]
    seen: Set[str] = set()

    while stack:
        node, d = stack.pop()
        # If we've hit a cycle, traversed past our stated depth, or touched a file that isn't from our source, throw away the node
        if node in seen or d <= 0 or not node.startswith(source):
            continue
        seen.add(node)
        for child in graph.get(node, {}):
            stack.append((child, d - 1))

    return seen
