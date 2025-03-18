from agent_network.network.executable import Executable
from agent_network.network.vertexes.vertex import FirstPartyVertex


class GroupVertex(FirstPartyVertex):
    def __init__(self, network, executable: Executable, params, results):
        super().__init__(network, executable, params, results)
        self.group = executable.id
        self.title = executable.title
        self.name = executable.name
        self.description = executable.description

    # def release(self):
    #     return self.executable.release()


class AgentVertex(FirstPartyVertex):
    def __init__(self, network, executable: Executable, params, results, group):
        super().__init__(network, executable, params, results)
        self.group = group
        self.title = executable.title
        self.name = executable.name
        self.description = executable.description

    # def release(self):
    #     usages, time_costs = self.executable.release()
    # usage_token_total_map = {}
    # total_time = 0
    # for usage in usages:
    #     usage_token_total_map.setdefault('completion_tokens', 0)
    #     usage_token_total_map.setdefault('total_tokens', 0)
    #     usage_token_total_map.setdefault('prompt_tokens', 0)
    #     usage_token_total_map['completion_tokens'] += usage.completion_token
    #     usage_token_total_map['total_tokens'] += usage.total_tokens
    #     usage_token_total_map['prompt_tokens'] += usage.prompt_tokens
    # for time_cost in time_costs:
    #     total_time += time_cost.usage_time
    # return usages, time_costs
