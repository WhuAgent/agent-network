from abc import abstractmethod
from agent_network.network.executable import Executable


class Network(Executable):
    def __init__(self, name, task, params, results):
        super().__init__(name, task)
        self.name = name
        self.task = task
        self.params = params
        self.results = results
        self.graphs = {}

    @abstractmethod
    def execute(self, input_content):
        pass

    def add_graph(self, name, graph):
        self.graphs[name] = graph

    def get_graph(self, name):
        assert name not in self.graphs, f"network: {self.name} already has graph named: {name}"
        return self.graphs[name]
