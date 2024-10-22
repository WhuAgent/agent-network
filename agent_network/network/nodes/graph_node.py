from agent_network.network.executable import Executable
import agent_network.pipeline.context as ctx
from agent_network.network.nodes.node import Node


class GroupNode(Node):
    def __init__(self, executable: Executable, group_name, group_task, params, results):
        super().__init__(Executable(group_name, group_task), params, results)
        self.group_name = group_name
        self.group_task = group_task
        self.executable = executable

    def execute(self, input_content, **kwargs):
        kwargs.update(ctx.retrieves_global([param["name"] for param in self.params]))
        results = self.executable.execute(input_content, **kwargs)
        ctx.registers(results)
        if self.results:
            ctx.registers_global(ctx.retrieves([result["name"] for result in self.results]))
        ctx.register_global(self.group_name, True)
        return results


class AgentNode(Node):
    def __init__(self, executable: Executable, agent_name, agent_task, params, results):
        super().__init__(Executable(agent_name, agent_task), params, results)
        self.agent_name = agent_name
        self.agent_task = agent_task
        self.executable = executable
