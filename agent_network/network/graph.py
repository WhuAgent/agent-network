from agent_network.network.executable import Executable
import agent_network.pipeline.context as ctx
import threading
from abc import abstractmethod


class Graph(Executable):
    def __init__(self, name, task, params, results):
        super().__init__(name, task)
        self.name = name
        self.task = task
        self.params = params
        self.results = results
        self.nodes = {}

    @abstractmethod
    def execute(self, start_node):
        pass

    def add_node(self, name, node):
        if name not in self.nodes:
            self.nodes[name] = node

    def get_node(self, name):
        return self.nodes[name]


# TODO 基于感知层去调度graph及其智能体
class GraphStart:
    def __init__(self, graph: Graph):
        self.graph = graph

    def execute(self, start_nodes, task):
        for start_node in start_nodes:
            assert start_node in self.graph.nodes, f"nodes: {start_node} is not in graph: {self.graph.name}"
        start_nodes = [self.graph.nodes[start_agent] for start_agent in start_nodes]
        nodes_threads = []
        for start_node in start_nodes:
            current_ctx = ctx.retrieve_global_all()
            node_thread = threading.Thread(
                target=lambda ne=start_node, ic=task if not task else self.graph.task: (
                    ctx.shared_context(current_ctx),
                    ne.execute(ic),
                    ctx.registers_global(ctx.retrieves([result["name"] for result in self.graph.results] if self.graph.results else []))
                )
            )
            nodes_threads.append(node_thread)

        for node_thread in nodes_threads:
            node_thread.start()
        for node_thread in nodes_threads:
            node_thread.join()

    def add_node(self, name, node):
        self.graph.add_node(name, node)

    def get_node(self, name):
        return self.graph.get_node(name)
