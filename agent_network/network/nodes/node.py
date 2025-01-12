from datetime import datetime
from agent_network.network.executable import Executable, ParameterizedExecutable
from agent_network.base import BaseAgent, BaseAgentGroup
import agent_network.pipeline.context as ctx
from agent_network.exceptions import RetryError, ReportError
from agent_network.pipeline.pipeline import Pipeline
import yaml
from agent_network.utils.logger import Logger
from agent_network.network.route import Route
from agent_network.evolution.base_evolution import BaseEvolutionAgent
from agent_network.network.nodes.graph_node import AgentNode


class Node(ParameterizedExecutable):
    def __init__(self, graph, executable: Executable, params, results):
        super().__init__(executable.name, executable.task, executable.description, params, results)
        self.name = executable.name
        self.task = executable.task
        self.description = executable.description
        self.executable = executable
        # todo 移除防止资源竞争
        self.next_executables: list[str] = []
        self.graph = graph

    def get_system_message(self):
        if isinstance(self.executable, BaseAgent):
            return self.executable.system_message
        return None

    def execute(self, messages, **kwargs):
        kwargs.update(ctx.retrieves([param["name"] for param in self.params]))
        if error_message := ctx.retrieve("graph_error_message"):
            kwargs["graph_error_message"] = error_message
        
        try:
            begin_t = datetime.now().timestamp()
            messages, results = self.executable.execute(messages, **kwargs)
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
            # raise Exception(e, "Task Failed")
            # TODO 识别到需要演化的信号
            sys_config_path = "config/System/pipline.yaml"
            logger = Logger("log/system")
            with open(sys_config_path, "r", encoding="UTF-8") as f:
                config = yaml.safe_load(f)
            # TODO 根据历史执行信息和异常信息生成演化task
            task = ""
            pipeline = Pipeline(task, config, logger)
            route = Route()
            context = {}
            context["task"] = task
            pipeline.execute(self.graph, route, task, context)
            new_config = pipeline.retrieve_result("config")
            new_agent = BaseEvolutionAgent(new_config, logger)
            self.graph.add_node(new_agent.name, AgentNode(self.graph, new_agent, new_agent.params, new_agent.results))
            # TODO 获取目标智能体组
            group: BaseAgentGroup = None
            group.add_agent(new_agent.name)
        else:
            end_t = datetime.now().timestamp()
            ctx.register_time(end_t - begin_t)
            default_next_executors = [exe for exe in self.next_executables] if len(self.next_executables) > 0 else None
            next_executors = [results.get("next_agent")] if results.get("next_agent") is not None else default_next_executors
            self.next_executables.clear()

        ctx.registers(results)
        if self.results:
            ctx.registers_global(ctx.retrieves([result["name"] for result in self.results]))

        if ctx.retrieve("graph_error_message"):
            ctx.delete("graph_error_message")
        return messages, results, next_executors

    def release(self):
        if self.executable is not None:
            return self.executable.release()
