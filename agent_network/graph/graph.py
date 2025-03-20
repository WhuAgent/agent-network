import uuid
import traceback

from agent_network.graph.history import History
from agent_network.network.network import Network
from agent_network.network.route import Route
from agent_network.graph.task_vertex import TaskVertex
import agent_network.graph.context as ctx
from agent_network.graph.trace import Trace
from agent_network.task.task_call import Parameter, TaskStatus
from agent_network.network.vertexes.third_party.executable import ThirdPartyExecutable, ThirdPartySchedulerExecutable


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

    def execute(self, network: Network, task, start_vertex="AgentNetworkPlanner", params=None, results=None):
        if results is None:
            results = ["results"]
        try:
            vertexes = network.get_vertexes()
            # TODO 分布式下如何处理vertex_messages
            for vertex in vertexes:
                if system_message := network.get_vertex(vertex).get_system_message():
                    self.vertex_messages[vertex] = [system_message]
                else:
                    self.vertex_messages[vertex] = []
            if "task" not in params.keys():
                params["task"] = task
            return self._execute_graph(network,
                                       network.route,
                                       [TaskVertex(id="start")],
                                       [TaskVertex(network.get_vertex(start_vertex))],
                                       [],
                                       params, results)
        except Exception as e:
            traceback.print_exc()
            self.release()
            raise Exception(e)

    def execute_task_call(self, graph, network: Network, start_vertex, params: list[Parameter], organizeId):
        if "trace_id" not in graph or "total_level" not in graph or "level_details" not in graph or graph[
            "total_level"] != len(graph["level_details"]):
            raise Exception(f"task: {graph['trace_id']}, graph error: {graph}")
        graph_level = graph["total_level"]
        # 按照执行图回放
        for level in range(graph_level):
            level_detail = graph["level_details"][level]
            self.trace.add_vertexes(level_detail["level_vertexes"])
            # 按照span注册上下文
            for level_span, span_detail in level_detail["level_spans"].items():
                span_params = span_detail["params"]
                for span_param in span_params:
                    ctx.register(span_param["name"], span_param["value"])
                span_results = span_detail["results"]
                for span_result in span_results:
                    ctx.register(span_result["name"], span_result["value"])
            # 恢复route
            for level_route_vertex, level_target_map in level_detail["level_routes"].items():
                level_route_vertexes = []
                for level_target in level_target_map.keys():
                    level_route_vertexes.append(network.get_vertex(level_target))
                self.trace.add_spans(network.get_vertex(level_route_vertex), level_route_vertexes)
        if graph_level > 0:
            graph_front = graph["level_details"][graph_level - 1]
            if "level_routes" not in graph_front:
                raise Exception(f"task: {graph['trace_id']}, graph error: {graph}")
        third_party_scheduler_executable = ThirdPartySchedulerExecutable(self.subtaskId, self.taskId, self, organizeId,
                                                                         None)
        try:
            vertexes = network.get_vertexes()
            if start_vertex not in vertexes:
                raise Exception(
                    f"task: {graph['trace_id']}, graph error, vertex not found: {start_vertex}, graph: {graph}")
            # TODO 分布式下如何处理vertex_messages
            for vertex in vertexes:
                if system_message := network.get_vertex(vertex).get_system_message():
                    self.vertex_messages[vertex] = [system_message]
                else:
                    self.vertex_messages[vertex] = []
            results = self._execute_graph(network,
                                          network.route,
                                          [TaskVertex(id="start")],
                                          [TaskVertex(network.get_vertex(start_vertex))],
                                          [],
                                          {param["name"]: param["value"] for param in params}, ["result"], organizeId)
            third_party_scheduler_executable.synchronize(TaskStatus.SUCCESS)
            return results
        except Exception as e:
            traceback.print_exc()
            third_party_scheduler_executable.synchronize(TaskStatus.FAILED)
            self.release()
            raise Exception(e)

    def _execute_graph(self,
                       network: Network,
                       route: Route,
                       father_task_vertexes: list[TaskVertex],
                       task_vertexes: list[TaskVertex],
                       third_party_next_task_vertexes: list[TaskVertex] = [],
                       params=None,
                       results=["result"],
                       organizeId=None):
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
        if len(third_party_next_task_vertexes) > 0:
            third_party_scheduler_executable = ThirdPartySchedulerExecutable(self.subtaskId, self.taskId, self,
                                                                             organizeId,
                                                                             self.trace.get_level_routes_front())
            third_party_scheduler_executable.execute()
        # TODO 由感知层根据任务激活决定触发哪些 Agent，现在默认线性执行所有 TaskNode
        next_task_vertexes: list[TaskVertex] = []
        third_party_next_task_vertexes: list[TaskVertex] = []
        for task_vertex in task_vertexes:
            current_next_task_vertexes = []
            # todo 讨论是否需要合并message到上下文中
            messages = self.vertex_messages[task_vertex.id]
            try:
                len_message = len(messages)

                self.execution_history.append(History(pre_executors=father_task_vertexes, cur_executor=task_vertex))
                self.cur_execution = self.execution_history[-1]

                # 更新 task_vertex 状态（开始运行）
                task_vertex.set_status(TaskStatus.RUNNING)

                cur_execution_result, next_executables = network.execute(task_vertex.id, messages)

                self.cur_execution.llm_messages = messages[len_message:]
                self.cur_execution.next_executors = next_executables

                # 更新 task_vertex 状态（成功运行收集结果）
                task_vertex.set_status(TaskStatus.SUCCESS)
                task_vertex.time_cost = self.cur_execution.time_cost
                for message in self.cur_execution.llm_messages:
                    task_vertex.token += message.token_num
                    task_vertex.token_cost += message.token_cost

                if task_vertex.id != "AgentNetworkPlanner" and ctx.retrieve("step") is not None:
                    ctx.register("step", ctx.retrieve("step") + 1)

                targets = next_executables if next_executables else route.search(task_vertex.id)

                for target in targets:
                    route.forward_message(task_vertex.id, target)
                    if target != "COMPLETE":
                        next_task_vertex = TaskVertex(network.get_vertex(target))
                        current_next_task_vertexes.append(next_task_vertex)

                self.trace.add_spans(task_vertex.executable, [nv.executable for nv in current_next_task_vertexes], messages)
                current_third_party_next_task_vertexes = [ns for ns in current_next_task_vertexes if
                                                          isinstance(ns.executable, ThirdPartyExecutable)]
                current_next_task_vertexes = [ns for ns in current_next_task_vertexes if
                                              not isinstance(ns.executable, ThirdPartyExecutable)]
                third_party_next_task_vertexes.extend(current_third_party_next_task_vertexes)
                next_task_vertexes.extend(current_next_task_vertexes)
            except Exception as e:
                self.release()
                raise Exception(e)
        if len(next_task_vertexes) > 0 or len(third_party_next_task_vertexes) > 0:
            return self._execute_graph(network, route, task_vertexes, next_task_vertexes,
                                       third_party_next_task_vertexes)
        else:
            return self.summarize_result(network, route, task_vertexes,
                                         TaskVertex(network.get_vertex("AgentNetworkSummarizer")))

    def summarize_result(self,
                         network: Network,
                         route: Route,
                         father_task_vertexes: list[TaskVertex],
                         task_vertex: TaskVertex):

        current_context = ctx.retrieves_all()
        ignored_context = ["$$$$$Graph$$$$$", "$$$$$GraphID$$$$$", "sub_tasks", "step"]
        valuable_context = {}
        for key, value in current_context.items():
            if key not in ignored_context:
                valuable_context[key] = value

        messages = self.vertex_messages[task_vertex.id]
        len_message = len(messages)

        self.execution_history.append(History(pre_executors=father_task_vertexes, cur_executor=task_vertex))
        self.cur_execution = self.execution_history[-1]

        # 更新 task_vertex 状态（开始运行）
        task_vertex.set_status(TaskStatus.RUNNING)

        cur_execution_result, next_executables = network.execute(task_vertex.id, messages, **valuable_context)

        self.cur_execution.llm_messages = messages[len_message:]
        self.cur_execution.next_executors = next_executables

        # 更新 task_vertex 状态（成功运行收集结果）
        task_vertex.set_status(TaskStatus.SUCCESS)
        task_vertex.time_cost = self.cur_execution.time_cost
        for message in self.cur_execution.llm_messages:
            task_vertex.token += message.token_num
            task_vertex.token_cost += message.token_cost

        return cur_execution_result

    def register_time_cost(self, time_cost):
        self.total_time += time_cost

    def retrieve_result(self, key):
        return ctx.retrieve_global(key)

    def retrieve_results(self, results=None):
        if results is None:
            return ctx.retrieves_all()
        return {key: ctx.retrieve(key) for key in results}

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
