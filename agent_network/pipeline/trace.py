import json
import uuid
from typing import Dict, List


class Trace:
    def __init__(self, id):
        assert id is not None, "Trace Id can not be None"
        self.id = id
        self.level = 0
        self.level_nodes: Dict[int, List] = {}
        self.level_spans: Dict[int, Dict] = {}
        self.level_routes: Dict[int, Dict[str, List]] = {}
        self.nodes = []
        self.nodes_count = 0

    def add_nodes(self, nodes):
        self.level += 1
        self.level_nodes[self.level] = nodes
        self.nodes_count += len(nodes)
        self.nodes.extend(nodes)

    def add_spans(self, node, next_nodes, messages=None, result=None):
        self.level_spans[self.level] = {node: {"messages": messages, "result": result,
                                               "spans": [Span(node, nn) for nn in next_nodes]}}
        self.level_routes.setdefault(self.level, {})
        self.level_routes[self.level].setdefault(node, [])
        self.level_routes[self.level][node].extend(next_nodes)

    def to_json(self):
        level_details = [{"level": i + 1, "level_nodes": self.level_nodes[i + 1] if i + 1 in self.level_nodes else [],
                          "level_spans": self.level_spans[i + 1] if i + 1 in self.level_spans else {},
                          "level_routes": self.level_routes[i + 1] if i + 1 in self.level_spans else {}}
                         for i in range(self.level)]
        repr_map = {
            "traceId": self.id,
            "total_level": self.level,
            "participated_nodes": list(set(self.nodes)),
            "nodes_count": self.nodes_count,
            "level_details": level_details
        }
        
        return json.dumps(repr_map, indent=4, ensure_ascii=False, default=lambda x: x.__dict__)

    def __repr__(self):
        level_details = [{"level": i + 1, "level_nodes": self.level_nodes[i + 1] if i + 1 in self.level_nodes else [],
                          "level_spans": self.level_spans[i + 1] if i + 1 in self.level_spans else {},
                          "level_routes": self.level_routes[i + 1] if i + 1 in self.level_spans else {}}
                         for i in range(self.level)]
        repr_map = {
            "traceId": self.id,
            "total_level": self.level,
            "participated_nodes": list(set(self.nodes)),
            "nodes_count": self.nodes_count,
            "level_details": level_details
        }
        return f"{repr_map}"


class Span:
    def __init__(self, parent_node, node):
        self.id = str(uuid.uuid4())
        self.parent_node = parent_node
        self.node = node

    @property
    def __dict__(self):
        return {
            "from": self.parent_node,
            "to": self.node
        }

    def __repr__(self):
        return f"'{self.parent_node} -> {self.node}'"
