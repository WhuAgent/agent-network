import json
import uuid
from typing import Dict, List
from agent_network.task.task_call import Parameter
import agent_network.graph.context as ctx
from agent_network.network.vertexes.vertex import Vertex
from agent_network.base import BaseAgent, BaseAgentGroup


class Trace:
    def __init__(self, id):
        assert id is not None, "Trace Id can not be None"
        self.id = id
        self.level = 0
        self.level_vertexes: Dict[int, List] = {}
        self.level_spans: Dict[int, Dict] = {}
        self.level_routes: Dict[int, Dict[str, Dict]] = {}
        self.vertexes = []
        self.vertexes_count = 0

    def add_vertexes(self, vertexes):
        self.level += 1
        self.level_vertexes[self.level] = vertexes
        self.vertexes_count += len(vertexes)
        self.vertexes.extend(vertexes)

    def add_spans(self, vertex: Vertex, next_vertexes: list[Vertex], messages=None):
        params_config = vertex.params
        results_config = vertex.results
        params_result = []
        results_result = []
        for param_config in params_config:
            params_result.append(Parameter(param_config.title, param_config.name, param_config.description, ctx.retrieve(param_config.name), param_config.type))
        for result_config in results_config:
            results_result.append(Parameter(result_config.title, result_config.name, result_config.description, ctx.retrieve(result_config.name), result_config.type))
        self.level_spans[self.level] = {vertex.name: {"messages": messages, "params": params_result, "results": results_result,
                                               "spans": [Span(vertex.name, nn.name) for nn in next_vertexes], "status": ""}}
        self.level_routes.setdefault(self.level, {})
        self.level_routes[self.level].setdefault(vertex.name, {})
        for next_vertex in next_vertexes:
            if isinstance(next_vertex.executable, BaseAgent):
                type = "agent"
            elif isinstance(next_vertex.executable, BaseAgentGroup):
                type = "group"
            else:
                # todo 如何判断tbot类型
                type = "tbot"
            params = [Parameter(param_config.title, param_config.name, param_config.description, ctx.retrieve(param_config.name), param_config.type) for param_config in next_vertex.params]
            self.level_routes[self.level][vertex.name][next_vertex.name] = {
                "type": type,
                "params": params
            }

    def get_level_routes_front(self):
        return self.level_routes[self.level]

    def __repr__(self):
        level_details = [{"level": i + 1, "level_vertexes": self.level_vertexes[i + 1] if i + 1 in self.level_vertexes else [],
                          "level_spans": self.level_spans[i + 1] if i + 1 in self.level_spans else {},
                          "level_routes": self.level_routes[i + 1] if i + 1 in self.level_spans else {}}
                         for i in range(self.level)]
        repr_map = {
            "trace_id": self.id,
            "total_level": self.level,
            "participated_vertexes": list(set(self.vertexes)),
            "vertexes_count": self.vertexes_count,
            "level_details": level_details
        }
        return f"{repr_map}"


class Span:
    def __init__(self, parent_vertex, vertex):
        self.id = str(uuid.uuid4())
        self.parent_vertex = parent_vertex
        self.vertex = vertex

    def __repr__(self):
        return f"'{self.parent_vertex} -> {self.vertex}'"
