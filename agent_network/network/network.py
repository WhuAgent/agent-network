from abc import abstractmethod
from agent_network.network.executable import Executable


class Network(Executable):
    def __init__(self, name, task, params, results):
        super().__init__(name, task, name)
        self.name = name
        self.task = task
        self.params = params
        self.results = results
        self.graphs = {}

    @abstractmethod
    def execute(self, input_content, **kwargs):
        pass

    def add_graph(self, name, graph):
        assert name not in self.graphs, f"network: {self.name} already has graph named: {name}"
        self.graphs[name] = graph

    def get_graph(self, name):
        assert name in self.graphs, f"network: {self.name} does not have graph named: {name}"
        return self.graphs[name]

    def release(self):
        for graph_name, graph in self.graphs.items():
            graph.release()
