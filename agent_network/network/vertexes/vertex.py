from datetime import datetime
from agent_network.network.executable import Executable, ParameterizedExecutable
from agent_network.base import BaseAgent
import agent_network.graph.context as ctx
from agent_network.exceptions import RetryError, ReportError


class Vertex(ParameterizedExecutable):
    def __init__(self, network, executable: Executable, params, results):
        super().__init__(executable.id, executable.description, params, results)
        self.name = executable.id
        self.description = executable.description
        self.executable = executable
        # todo 移除防止资源竞争
        self.next_executables: list[str] = []
        self.network = network

    def get_system_message(self):
        if isinstance(self.executable, BaseAgent):
            return self.executable.system_message
        return None

    def execute(self, messages=None, **kwargs):
        kwargs.update(ctx.retrieves([param["name"] for param in self.params]))
        if error_message := ctx.retrieve("graph_error_message"):
            kwargs["graph_error_message"] = error_message
        begin_t = datetime.now().timestamp()
        try:
            results, next_executors = self.executable.execute(messages, **kwargs)
        except RetryError as e:
            end_t = datetime.now().timestamp()
            ctx.register_time(end_t - begin_t)
            if kwargs.get("graph_error_message"):
                kwargs["graph_error_message"].append(e.message)
            else:
                kwargs["graph_error_message"] = [e.message]
            if len(kwargs["graph_error_message"]) < 5:
                results, next_executors = self.execute(messages, **kwargs)
            else:
                raise Exception(e, "Task Failed")
        except ReportError as e:
            end_t = datetime.now().timestamp()
            ctx.register_time(end_t - begin_t)
            results = e.error_message
            next_executors = [e.next_vertex]
            ctx.register("graph_error_message", [e.error_message])
            return results, next_executors
        except Exception as e:
            raise Exception(e, "Task Failed")
        else:
            end_t = datetime.now().timestamp()
            ctx.register_time(end_t - begin_t)
            default_next_executors = [exe for exe in self.next_executables] if len(self.next_executables) > 0 else None
            next_executors =  next_executors or default_next_executors
            if next_executors and not isinstance(next_executors, list):
                next_executors = [next_executors]
            self.next_executables.clear()

        ctx.registers(results)
        if self.results:
            ctx.registers_global(ctx.retrieves([result["name"] for result in self.results]))

        if ctx.retrieve("graph_error_message"):
            ctx.delete("graph_error_message")
        return results, next_executors

    def release(self):
        if self.executable is not None:
            return self.executable.release()


class ThirdPartyVertex(Vertex):
    def __init__(self, network, executable: Executable, params, results):
        super().__init__(network, executable, params, results)


class FirstPartyVertex(Vertex):
    def __init__(self, network, executable: Executable, params, results):
        super().__init__(network, executable, params, results)
