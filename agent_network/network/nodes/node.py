from agent_network.network.executable import Executable, ParameterizedExecutable
import agent_network.pipeline.context as ctx
from agent_network.base import BaseAgent


class Node(ParameterizedExecutable):
    def __init__(self, executable: Executable, params, results):
        super().__init__(executable.name, executable.task, params, results)
        self.name = executable.name
        self.executable = executable

    def execute(self, input_content, **kwargs):
        # an agent chain runs sequentially with sharing context
        if isinstance(self.executable, BaseAgent):
            next_task, results = self.executable.agent_base(
                input_content if not input_content else self.executable.task,
                **ctx.retrieves([param["name"] for param in self.params]))
            ctx.registers(results)
            ctx.registers_global(ctx.retrieves([result["name"] for result in self.results]))
        else:
            next_task = self.executable.execute(input_content if not input_content else self.executable.task)
        return next_task
