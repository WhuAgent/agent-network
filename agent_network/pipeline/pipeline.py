from agent_network.network.graph import Graph
from agent_network.network.nodes.graph_node import GroupNode
from agent_network.network.route import Route
from agent_network.base import BaseAgentGroup
import yaml
import agent_network.pipeline.context as ctx


class Pipeline:
    def __init__(self, task, config, logger):
        self.task = task
        self.config = config
        self.logger = logger
        self.nodes = []

        for item in self.config["context"]:
            if item["type"] == "str":
                ctx.register(item["name"], self.task if item["name"] == "task" else "")
            elif item["type"] == "list":
                ctx.register(item["name"], [])

    def load_graph(self, graph):
        # 加载节点
        for group in self.config["group_pipline"]:
            group_name, group_config_path = list(group.items())[0]
            with open(group_config_path, "r", encoding="utf-8") as f:
                configs = yaml.safe_load(f)
                graph.add_node(group_name,
                               GroupNode(BaseAgentGroup(graph, configs, self.logger),
                                         configs["params"],
                                         configs["results"]))

        return graph

    def load_route(self, graph: Graph, route: Route):
        for node_name, node_instance in graph.nodes.items():
            route.register_node(node_name, node_instance.description)

        for item in graph.routes:
            route.register_contact(item["source"], item["target"], item["message_type"])

        return route

    def execute(self, graph: Graph, route: Route, task: str, context=None):
        if context:
            ctx.registers(context)
        # 加载任务节点
        graph = self.load_graph(graph)
        # 加载路由
        route = self.load_route(graph, route)
        # TODO 由感知层根据任务激活决定触发哪些 Agent，现在默认所有 Group 都多线程执行 current_task
        node = self.config["start_node"]
        message = task
        while message != "COMPLETE":
            result, next_node = graph.execute(node, message, graph_next_executors=route.get_contactions(node))
            next_node, message = route.forward_message(node, next_node, result)
            node = next_node
        return result

    @staticmethod
    def retrieve_result(key):
        return ctx.retrieve_global(key)

    @staticmethod
    def retrieve_results():
        return ctx.retrieve_global_all()

    @staticmethod
    def release():
        ctx.release()
        ctx.release_global()
