import uuid
import traceback

from agent_network.graph.history import History
from agent_network.network.network import Network
from agent_network.network.route import Route
from agent_network.graph.task_vertex import TaskVertex
import agent_network.graph.context as ctx
from agent_network.graph.trace import Trace


class Graph:
    def __init__(self, logger, id=None):
        self.logger = logger
        self.vertexes = []
        self.step = 0
        if id is None:
            self.id = str(uuid.uuid4())
        else:
            self.id = id

        self.trace = Trace(self.id)
        self.total_time = 0

        self.message_num = 0
        self.execution_history: list[History] = []
        self.cur_execution = None
        self.vertex_messages = dict()

        ctx.register_graph(id, self)

    # def load_graph(self, graph: Network):
    #     # 加载节点
    #     for group in self.config["group_pipline"]:
    #         group_config_path = list(group.values())[0]
    #         with open(group_config_path, "r", encoding="utf-8") as f:
    #             configs = yaml.safe_load(f)
    #             if "ref_id" in configs:
    #                 group = self.import_group(graph, configs)
    #             else:
    #                 group = BaseAgentGroup(graph, graph.route, configs, self.logger)
    #             agents = group.load_agents()
    #
    #             graph.add_vertex(group.name, GroupNode(graph, group, group.params, group.results))
    #             for agent in agents:
    #                 graph.add_vertex(agent.name, AgentNode(graph, agent, agent.params, agent.results, group.name))
    #
    #             graph.add_route(group.name, group.name, group.start_agent, "start", "hard")
    #             for route in group.routes:
    #                 if "rule" not in route:
    #                     route["rule"] = "soft"
    #                 graph.add_route(group.name, route["source"], route["target"], route["type"], route["rule"])
    #
    #     vertexes = graph.get_vertexes()
    #     # TODO 分布式下如何处理vertex_messages
    #     for vertex in vertexes:
    #         if system_message := graph.get_vertex(vertex).get_system_message():
    #             self.vertex_messages[vertex] = [system_message]
    #         else:
    #             self.vertex_messages[vertex] = []
    #     graph.refresh_vertexes_from_clients()
    #     graph.load_route()

    # def import_group(self, graph, group_config):
    #     if "load_type" in group_config and group_config["load_type"] == "module":
    #         group_module = importlib.import_module(group_config["loadModule"])
    #         group_class = getattr(group_module, group_config["loadClass"])
    #         group_instance = group_class(graph, graph.route, group_config, self.logger)
    #     else:
    #         raise Exception("Group load type must be module!")
    #     return group_instance

    def execute(self, network: Network, start_vertex, params=None, results=["result"]):
        try:
            vertexes = network.get_vertexes()
            # TODO 分布式下如何处理vertex_messages
            for vertex in vertexes:
                if system_message := network.get_vertex(vertex).get_system_message():
                    self.vertex_messages[vertex] = [system_message]
                else:
                    self.vertex_messages[vertex] = []
            return self._execute_graph(network,
                                       network.route,
                                       [TaskVertex(id="start")],
                                       [TaskVertex(network.get_vertex(start_vertex))],
                                       params, results)
        except Exception as e:
            traceback.print_exc()
            self.release()
            raise Exception(e)

    def _execute_graph(self,
                       network: Network,
                       route: Route,
                       father_task_vertexes: list[TaskVertex],
                       task_vertexes: list[TaskVertex],
                       params=None,
                       results=["result"]):
        if task_vertexes is None or len(task_vertexes) == 0:
            return
        self.trace.add_vertexes([n.id for n in task_vertexes])
        self.step += 1
        # max_step = self.config.get("max_step", 100)
        max_step = 100
        if self.step > max_step:
            self.release()
            raise Exception("Max step reached, Task Failed!")
        if params:
            ctx.registers(params)
        # TODO 由感知层根据任务激活决定触发哪些 Agent，现在默认线性执行所有 TaskNode
        next_task_vertexes: list[TaskVertex] = []
        for task_vertex in task_vertexes:
            current_next_task_vertexes = []
            # todo 讨论是否需要合并message到上下文中
            messages = self.vertex_messages[task_vertex.id]
            try:
                len_message = len(messages)

                self.execution_history.append(History(pre_executors=father_task_vertexes, cur_executor=task_vertex))
                self.cur_execution = self.execution_history[-1]

                cur_execution_result, next_executables = network.execute(task_vertex.id, messages)

                self.cur_execution.llm_messages = messages[len_message:]
                self.cur_execution.next_executors = next_executables

                # self.load_route(graph, route)
                if next_executables is None:
                    # 根据result和当前节点执行动态路由搜索逻辑
                    targets = route.search(task_vertex.id, ctx.retrieves_all(), results)
                    for target in targets:
                        if target != "COMPLETE":
                            next_task_vertex = TaskVertex(network.get_vertex(target))
                            current_next_task_vertexes.append(next_task_vertex)
                else:
                    for next_executable in next_executables:
                        target = route.forward_message(task_vertex.id, next_executable)
                        # if not leaf vertex
                        if target != "COMPLETE":
                            next_task_vertex = TaskVertex(network.get_vertex(next_executable))
                            current_next_task_vertexes.append(next_task_vertex)
                self.trace.add_spans(task_vertex.id, [nv.id for nv in current_next_task_vertexes], messages, cur_execution_result)
                next_task_vertexes.extend(current_next_task_vertexes)
            except Exception as e:
                self.release()
                raise Exception(e)
        if len(next_task_vertexes) > 0:
            self._execute_graph(network, route, task_vertexes, next_task_vertexes)
        return ctx.retrieves_all()

    def register_time_cost(self, time_cost):
        self.total_time += time_cost

    def retrieve_result(self, key):
        return ctx.retrieve_global(key)

    def retrieve_results(self, results):
        return {key: ctx.retrieve_global(key) for key in results}

    def release(self):
        total_token_num = 0
        total_token_cost = 0
        total_time = self.total_time

        for execution in self.execution_history:
            for message in execution.llm_messages:
                total_token_num += message.token_num
                total_token_cost += message.token_cost

        self.logger.log("network", f"PIPELINE {self.id} TOTSL TOKEN NUM: {total_token_num} COST: {total_token_cost}",
                        "Agent-Network")
        self.logger.log("network", f"PIPELINE {self.id} TIME COST TOTAL: {self.total_time}", "Agent-Network")
        self.logger.log("network", f"PIPELINE {self.id} has been released", "Agent-Network")
        ctx.release()
        ctx.release_global()

        self.logger.categorize_log()
        self.logger.log_trace(self.trace)

        self.total_time = 0

        self.message_num = 0
        self.execution_history: list[History] = []
        self.cur_execution = None
        self.vertex_messages = dict()

        return total_token_num, total_token_cost, total_time
