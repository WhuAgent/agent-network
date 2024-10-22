from agent_network.network.nodes.graph_node import GroupNode
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
                ctx.register_global(item["name"], self.task if item["name"] == "task" else "")
            elif item["type"] == "list":
                ctx.register_global(item["name"], [])

    def load(self, graph):
        group_names = []
        for group in self.config["group_pipline"]:
            group_name, group_config_path = list(group.items())[0]
            with open(group_config_path, "r", encoding="utf-8") as f:
                configs = yaml.safe_load(f)
                graph.add_node(group_name,
                               GroupNode(BaseAgentGroup(configs, self.logger),
                                         group_name,
                                         configs["task"],
                                         configs["params"],
                                         configs["results"]))
                group_names.append(group_name)
        # return group_names
        return group_names, graph

    def execute(self, graph):
        group_names, graph = self.load(graph)
        # TODO 由感知层根据任务激活决定触发哪些Agent，现在默认所有Group都多线程执行current_task
        graph.execute(group_names, self.task)

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
