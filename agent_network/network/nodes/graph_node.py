from agent_network.network.executable import Executable
from agent_network.network.nodes.node import Node


class GroupNode(Node):
    def __init__(self, executable: Executable, params, results):
        super().__init__(executable, params, results)


class AgentNode(Node):
    def __init__(self, executable: Executable, params, results):
        super().__init__(executable, params, results)
