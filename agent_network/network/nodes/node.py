from abc import abstractmethod

from agent_network.network.executable import Executable, ParameterizedExecutable
import agent_network.pipeline.context as ctx


class Node(ParameterizedExecutable):
    def __init__(self, executable: Executable, params, results):
        super().__init__(executable.name, executable.task, params, results)
        self.name = executable.name
        self.executable = executable

    def execute(self, input_content, **kwargs):
        kwargs.update(ctx.retrieves_global([param["name"] for param in self.params]))
        results = self.executable.execute(input_content, **kwargs)
        ctx.registers(results)
        if self.results:
            ctx.registers_global(ctx.retrieves([result["name"] for result in self.results]))
        return results
