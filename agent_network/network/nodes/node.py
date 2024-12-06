from agent_network.network.executable import Executable, ParameterizedExecutable
import agent_network.pipeline.context as ctx
from agent_network.exceptions import RetryError, ReportError


class Node(ParameterizedExecutable):
    def __init__(self, executable: Executable, params, results):
        super().__init__(executable.name, executable.task, executable.description, params, results)
        self.name = executable.name
        self.task = executable.task
        self.description = executable.description
        self.executable = executable
        self.next_executables: [str] = []

    def execute(self, input_content, **kwargs):
        kwargs.update(ctx.retrieves([param["name"] for param in self.params]))
        if error_message := ctx.retrieve("graph_error_message"):
            kwargs["graph_error_message"] = error_message
        
        try:
            results = self.executable.execute(input_content, **kwargs)
            default_next_executors = self.next_executables if len(self.next_executables) > 0 else None
            next_executors = [results.get("next_agent")] if results.get("next_agent") is not None else default_next_executors
        except RetryError as e:
            if kwargs.get("graph_error_message"):
                kwargs["graph_error_message"].append(e.message)
            else:
                kwargs["graph_error_message"] = [e.message]
            if len(kwargs["graph_error_message"]) < 5:
                results, next_executors = self.execute(input_content, **kwargs)
            else:
                raise Exception(e, "Task Failed")
        except ReportError as e:
            results = e.error_message
            next_executors = [e.next_node]
            ctx.register("graph_error_message", results)
            return results, next_executors
        except Exception as e:
            raise Exception(e, "Task Failed")
        
        ctx.registers(results)
        if self.results:
            ctx.registers_global(ctx.retrieves([result["name"] for result in self.results]))
        
        if ctx.retrieve("graph_error_message"):
            ctx.delete("graph_error_message")
        return results, next_executors
