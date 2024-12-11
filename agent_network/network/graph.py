from agent_network.network.executable import Executable
from agent_network.network.route import Route
import agent_network.pipeline.context as ctx
import threading
from abc import abstractmethod


class Graph(Executable):
    def __init__(self, name, task, description, start_node, params, results):
        super().__init__(name, task, description)
        self.name = name
        self.task = task
        
        self.params = params
        self.results = results

        self.num_nodes = 0
        self.start_node = start_node
        
        self.nodes = {}
        self.routes = []

    @abstractmethod
    def execute(self, node, message, **kwargs):
        current_ctx = ctx.retrieve_global_all()
        ctx.shared_context(current_ctx)
        result, next_execution, usage_info = self.nodes.get(node).execute(message, **kwargs)
        ctx.registers_global(ctx.retrieves([result["name"] for result in self.results] if self.results else []))
        
        return result, next_execution, usage_info

    def add_node(self, name, node: Executable):
        if name not in self.nodes:
            self.nodes[name] = node
            self.num_nodes += 1

    def get_node(self, name) -> Executable:
        return self.nodes[name]
    
    def add_route(self, source, target, message_type):
        self.routes.append({
            "source": source,
            "target": target,
            "message_type": message_type
        })



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
