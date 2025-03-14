from datetime import datetime
from agent_network.network.executable import Executable, ParameterizedExecutable
from agent_network.base import BaseAgent
import agent_network.pipeline.new_context.local as ctx
from agent_network.exceptions import RetryError, ReportError


class Node(ParameterizedExecutable):
    def __init__(self, executable: Executable, params, results):
        super().__init__(executable.name, executable.task, executable.description, params, results)
        self.name = executable.name
        self.task = executable.task
        self.description = executable.description
        self.executable = executable
        # todo 移除防止资源竞争
        self.next_executables: list[str] = []

    def get_system_message(self):
        if isinstance(self.executable, BaseAgent):
            return self.executable.system_message
        return None

    def execute(self, messages, **kwargs):
        self.params = self.params or []
        for param in self.params:
            if param.get("type") == "attribute":
                kwargs.update({param.get("name"): ctx.retrieve(param.get("name"))})
            elif param.get("type") == "method":
                kwargs.update({param.get("name"): ctx.execute(param.get("name"), action_type="retrieve", **param.get("args"))})
        # kwargs.update(ctx.retrieves([param["name"] for param in self.params]))
        if error_message := ctx.retrieve("graph_error_message"):
            kwargs["graph_error_message"] = error_message
        
        try:
            begin_t = datetime.now().timestamp()
            messages, results, next_executors = self.executable.execute(messages, **kwargs)
        except RetryError as e:
            end_t = datetime.now().timestamp()
            ctx.register_time(end_t - begin_t)
            if kwargs.get("graph_error_message"):
                kwargs["graph_error_message"].append(e.message)
            else:
                kwargs["graph_error_message"] = [e.message]
            if len(kwargs["graph_error_message"]) < 5:
                messages, results, next_executors = self.execute(messages, **kwargs)
            else:
                raise Exception(e, "Task Failed")
        except ReportError as e:
            end_t = datetime.now().timestamp()
            ctx.register_time(end_t - begin_t)
            results = e.error_message
            next_executors = [e.next_node]
            ctx.register("graph_error_message", [e.error_message])
            return messages, results, next_executors
        except Exception as e:
            raise Exception(e, "Task Failed")
        else:
            # TODO default_next_executors 其实没用
            end_t = datetime.now().timestamp()
            ctx.register_time(end_t - begin_t)
            default_next_executors = [exe for exe in self.next_executables] if len(self.next_executables) > 0 else None
            next_executors = next_executors or default_next_executors
            if not isinstance(next_executors, list):
                    next_executors = [next_executors]
            self.next_executables.clear()

        ctx.registers(results)
        for result in self.results:
            if result.get("type") == "attribute":
                ctx.register(result.get("name"), results.get(result.get("name")))
            elif result.get("type") == "method":
                ctx.execute(result.get("name"), action_type="register", **result.get("args"))
        if self.results:
            # ctx.registers_global(ctx.retrieves([result["name"] for result in self.results]))
            pass

        if ctx.retrieve("graph_error_message"):
            ctx.delete("graph_error_message")
        return messages, results, next_executors

    def release(self):
        if self.executable is not None:
            return self.executable.release()
