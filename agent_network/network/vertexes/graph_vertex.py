from agent_network.network.executable import Executable
from agent_network.network.vertexes.vertex import FirstPartyVertex, ThirdPartyVertex


class GroupVertex(FirstPartyVertex):
    def __init__(self, network, executable: Executable, params, results):
        super().__init__(network, executable, params, results)
        self.group = executable.id
        self.title = executable.title
        self.name = executable.name
        self.description = executable.description


class AgentVertex(FirstPartyVertex):
    def __init__(self, network, executable: Executable, params, results, group):
        super().__init__(network, executable, params, results)
        self.group = group
        self.title = executable.title
        self.name = group + "/" + executable.name
        self.description = executable.description


class ThirdPartyGroupVertex(ThirdPartyVertex):
    def __init__(self, network, executable: Executable, params, results):
        super().__init__(network, executable, params, results)
        self.title = executable.title
        self.name = executable.name
        self.description = executable.description


class ThirdPartyAgentVertex(ThirdPartyVertex):
    def __init__(self, network, executable: Executable, params, results):
        super().__init__(network, executable, params, results)
        self.title = executable.title
        self.name = executable.name
        self.description = executable.description
