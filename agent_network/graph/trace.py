import random


class Trace:
    def __init__(self, id):
        assert id is not None, "Trace Id can not be None"
        self.id = id
        self.level = 0
        self.level_vertexes: dict[int, list] = {}
        self.level_spans: dict[int, dict] = {}
        self.level_routes: dict[int, dict[str, list]] = {}
        self.vertexes = []
        self.vertexes_count = 0

    def add_vertexes(self, vertexes):
        self.level += 1
        self.level_vertexes[self.level] = vertexes
        self.vertexes_count += len(vertexes)
        self.vertexes.extend(vertexes)

    def add_spans(self, vertex, next_vertexes, messages=None, result=None):
        self.level_spans[self.level] = {vertex: {"messages": messages, "result": list(result.keys()),
                                                 "spans": [Span(vertex, nn) for nn in next_vertexes]}}
        self.level_routes.setdefault(self.level, {})
        self.level_routes[self.level].setdefault(vertex, [])
        self.level_routes[self.level][vertex].extend(next_vertexes)

    def __repr__(self):
        level_details = [
            {"level": i + 1, "level_vertexes": self.level_vertexes[i + 1] if i + 1 in self.level_vertexes else [],
             "level_spans": self.level_spans[i + 1] if i + 1 in self.level_spans else {},
             "level_routes": self.level_routes[i + 1] if i + 1 in self.level_spans else {}}
            for i in range(self.level)]
        repr_map = {
            "traceId": self.id,
            "total_level": self.level,
            "participated_vertexes": list(set(self.vertexes)),
            "vertexes_count": self.vertexes_count,
            "level_details": level_details
        }
        return f"{repr_map}"


class Span:
    def __init__(self, parent_vertex, vertex):
        self.id = str(random.random())
        self.parent_vertex = parent_vertex
        self.vertex = vertex

    def __repr__(self):
        return f"'{self.parent_vertex} -> {self.vertex}'"
