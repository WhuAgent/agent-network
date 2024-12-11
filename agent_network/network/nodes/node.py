from abc import abstractmethod
from datetime import datetime

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
        self.next_excutions = []

    def add_route(self, target, message_type):
        self.route.add_contact(target, message_type)

    def add_message(self, role, content):
        self.executable.add_message(role, content)

    def execute(self, input_content, retry=False, **kwargs):
        kwargs.update(ctx.retrieves([param["name"] for param in self.params]))
        if error_message := ctx.retrieve("graph_error_message"):
            kwargs["graph_error_message"] = error_message
        
        try:
            if not retry:
                self.executable.cur_execution_cost = {
                    "time": 0,
                    "llm_usage_history": []
                }
                begin_t = datetime.now()

            results = self.executable.execute(input_content, **kwargs)
            defalut_next_executor = self.next_excutions[0] if len(self.next_excutions) > 0 else None
            next_executor = results.get("next_agent", defalut_next_executor)
        except RetryError as e:
            if kwargs.get("graph_error_message"):
                kwargs["graph_error_message"].append(e.message)
            else:
                kwargs["graph_error_message"] = [e.message]
            if len(kwargs["graph_error_message"]) < 5:
                results, next_executor = self.execute(input_content, retry=True, **kwargs)
            else:
                raise Exception("Task Failed")
        except ReportError as e:
            results = e.error_message
            next_executor = e.next_node
            ctx.register("graph_error_message", [results])

            end_t = datetime.now()
            self.executable.cur_execution_cost["time"] = end_t - begin_t
            return results, next_executor, self.executable.cur_execution_cost
        
        ctx.registers(results)
        if self.results:
            ctx.registers_global(ctx.retrieves([result["name"] for result in self.results]))
        
        if ctx.retrieve("graph_error_message"):
            ctx.delete("graph_error_message")

        if not retry:
            end_t = datetime.now()
            self.executable.cur_execution_cost["time"] = end_t - begin_t
            return results, next_executor, self.executable.cur_execution_cost
        else:
            return results, next_executor
