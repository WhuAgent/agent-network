from agent_network.network.executable import Executable
import agent_network.pipeline.context as ctx
import threading
from abc import abstractmethod


class Route:
    def __init__(self, source, target, type):
        self.source = source
        self.target = target
        self.type = type

    def execute(self, graph, task):
        if self.source == "start":
            graph.get_node(self.target).execute(task)
        elif self.target == "end":
            return
        else:
            # TODO 根据type进行消息传递
            graph.get_node(self.target).execute(task)
