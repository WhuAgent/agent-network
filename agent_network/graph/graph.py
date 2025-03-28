import uuid
import traceback

from agent_network.graph.history import History
from agent_network.network.network import Network
from agent_network.network.route import Route
from agent_network.task.vertex import TaskVertex
from agent_network.utils.task import get_task_type
import agent_network.graph.context as ctx
from agent_network.graph.trace import Trace
from agent_network.task.manager import TaskManager
from agent_network.task.task_call import Parameter, TaskStatus
from agent_network.network.vertexes.third_party.executable import ThirdPartySchedulerExecutable
from agent_network.network.vertexes.vertex import ThirdPartyVertex
from agent_network.utils.llm.message import Message
from agent_network.utils.logger import Logger


class Graph:
    def __init__(self, logger=Logger("log"), id=None, max_step=100):
        self.logger = logger
        
        self.max_step = max_step
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
        
        self.task_manager = TaskManager()

        ctx.register_graph(self.id, self)

    def execute(self, network: Network, task, start_vertex="AgentNetworkPlannerGroup/AgentNetworkPlanner", params=None,
                results=None):
        if results is None:
            results = ["results"]
        try:
            task_id = self.task_manager.add_task(task, network.get_vertex(start_vertex))
            self.task_manager.cur_execution = [task_id]
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
                                       [TaskVertex(network.get_vertex(start_vertex), task)],
                                       [],
                                       params, results)
        except Exception as e:
            traceback.print_exc()
            self.release()
            raise Exception(e)

    def execute_task_call(self, sub_task, graph, network: Network, start_vertex, params: list[Parameter], organizeId):
        if "trace_id" not in graph or "total_level" not in graph or "level_details" not in graph or graph[
            "total_level"] != len(graph["level_details"]):
            raise Exception(f"task: {graph['trace_id']}, graph error: {graph}")
        graph_level = graph["total_level"]
        # 按照执行图回放
        for level in range(graph_level):
            level_detail = graph["level_details"][level]
            self.trace.add_vertexes(level_detail["level_vertexes"])
            # 恢复route
            level_route_map = {}
            for level_route_vertex, level_target_map in level_detail["level_routes"].items():
                level_route_vertexes = []
                for level_target, level_target_detail in level_target_map.items():
                    ntv = TaskVertex(network.get_vertex(level_target), level_target_detail["task"])
                    ntv.type = level_target_detail["type"]
                    level_route_vertexes.append(ntv)
                level_route_map[level_route_vertex] = level_route_vertexes
            # 按照span注册上下文
            for level_span_vertex, span_detail in level_detail["level_spans"].items():
                span_params = span_detail["params"]
                for span_param in span_params:
                    ctx.register(span_param["name"], span_param["value"])
                span_results = span_detail["results"]
                for span_result in span_results:
                    ctx.register(span_result["name"], span_result["value"])
                spans = span_detail["spans"]
                messages = span_detail["messages"]
                recovery_messages = []
                for message in messages:
                    recovery_message = Message(message["role"], message["content"])
                    recovery_message.token_num = message["token"]
                    recovery_message.token_cost = message["cost"]
                    recovery_messages.append(recovery_message)
                self.trace.add_spans(TaskVertex(network.get_vertex(level_span_vertex), span_detail["task"], None,
                                                span_detail["status"], span_detail["token"], span_detail["cost"],
                                                span_detail["time"]),
                                     level_route_map[level_span_vertex], recovery_messages)
        if "planning_result" in graph:
            self.trace.set_subtasks(graph["planning_result"].get("subtasks"), graph["planning_result"].get("step"))
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
                                          [TaskVertex(network.get_vertex(start_vertex), sub_task)],
                                          [],
                                          {param["name"]: param["value"] for param in params}, ["result"],
                                          organizeId,
                                          start_vertex == "AgentNetworkSummarizerGroup/AgentNetworkSummarizer")
            third_party_scheduler_executable.synchronize(TaskStatus.SUCCESS)
            return results
        except Exception as e:
            traceback.print_exc()
            third_party_scheduler_executable.synchronize(TaskStatus.FAILED)
            self.release()
            raise Exception(e)

    def execute_task_summary(self, sub_task, graph, network: Network, start_vertex, params: list[Parameter],
                             organizeId):
        if "trace_id" not in graph or "total_level" not in graph or "level_details" not in graph or graph[
            "total_level"] != len(graph["level_details"]):
            raise Exception(f"task: {graph['trace_id']}, graph error: {graph}")
        graph_level = graph["total_level"]
        # 按照执行图回放
        for level in range(graph_level):
            level_detail = graph["level_details"][level]
            self.trace.add_vertexes(level_detail["level_vertexes"])
            # 恢复route
            level_route_map = {}
            for level_route_vertex, level_target_map in level_detail["level_routes"].items():
                level_route_vertexes = []
                for level_target, level_target_detail in level_target_map.items():
                    ntv = TaskVertex(network.get_vertex(level_target), level_target_detail["task"])
                    ntv.type = level_target_detail["type"]
                    level_route_vertexes.append(ntv)
                level_route_map[level_route_vertex] = level_route_vertexes
            # 按照span注册上下文
            for level_span_vertex, span_detail in level_detail["level_spans"].items():
                span_params = span_detail["params"]
                for span_param in span_params:
                    ctx.register(span_param["name"], span_param["value"])
                span_results = span_detail["results"]
                for span_result in span_results:
                    ctx.register(span_result["name"], span_result["value"])
                spans = span_detail["spans"]
                messages = span_detail["messages"]
                recovery_messages = []
                for message in messages:
                    recovery_message = Message(message["role"], message["content"])
                    recovery_message.token_num = message["token"]
                    recovery_message.token_cost = message["cost"]
                    recovery_messages.append(recovery_message)
                self.trace.add_spans(TaskVertex(network.get_vertex(level_span_vertex), span_detail["task"], None,
                                                span_detail["status"], span_detail["token"], span_detail["cost"],
                                                span_detail["time"]),
                                     level_route_map[level_span_vertex], recovery_messages)
        if graph_level > 0:
            graph_front = graph["level_details"][graph_level - 1]
            if "level_routes" not in graph_front:
                raise Exception(f"task: {graph['trace_id']}, graph error: {graph}")
        try:
            vertexes = network.get_vertexes()
            if start_vertex not in vertexes:
                raise Exception(
                    f"task: {graph['trace_id']}, graph error, vertex not found: {start_vertex}, graph: {graph}")
            for vertex in vertexes:
                if system_message := network.get_vertex(vertex).get_system_message():
                    self.vertex_messages[vertex] = [system_message]
                else:
                    self.vertex_messages[vertex] = []
            if params:
                ctx.registers_params(params)
            ctx.register("executionGraph", graph)
            ctx.register("task", sub_task)
            results = self.summarize_result(network, network.route, [TaskVertex(id="start")],
                                            TaskVertex(network.get_vertex(
                                                "AgentNetworkSummarizerGroup/AgentNetworkSummarizer"),
                                                       f"summarize the total progress of the execution graph of the task: {sub_task}"))
            third_party_scheduler_executable = ThirdPartySchedulerExecutable(self.subtaskId, self.taskId, self,
                                                                             organizeId,
                                                                             None)
            third_party_scheduler_executable.summary(results.get('agent_network_summarize_reasoning'),
                                                     results.get('agent_network_final_result'))
            return results
        except Exception as e:
            traceback.print_exc()
            self.release()
            raise Exception(e)

    def execute_task_plan(self, sub_task, graph, network: Network, start_vertex, params: list[Parameter],
                          organizeId):
        if "trace_id" not in graph or "total_level" not in graph or "level_details" not in graph or graph[
            "total_level"] != len(graph["level_details"]):
            raise Exception(f"task: {graph['trace_id']}, graph error: {graph}")
        graph_level = graph["total_level"]
        if graph_level > 0:
            raise Exception(f"task: {graph['trace_id']}, plan error with graph: {graph}")
        next_task_vertexes = []
        third_party_next_task_vertexes = []
        try:
            vertexes = network.get_vertexes()
            if start_vertex not in vertexes:
                raise Exception(
                    f"task: {graph['trace_id']}, graph error, vertex not found: {start_vertex}, graph: {graph}")
            for vertex in vertexes:
                if system_message := network.get_vertex(vertex).get_system_message():
                    self.vertex_messages[vertex] = [system_message]
                else:
                    self.vertex_messages[vertex] = []
            ctx.register("task", sub_task)
            self.trace.add_vertexes([start_vertex])
            if params:
                ctx.registers_params(params)
            task_vertex = TaskVertex(network.get_vertex(start_vertex), sub_task)
            messages = self.vertex_messages[start_vertex]
            len_message = len(messages)

            self.execution_history.append(History(pre_executors=[TaskVertex(id="start")], cur_executor=task_vertex))
            self.cur_execution = self.execution_history[-1]

            # 更新 task_vertex 状态（开始运行）
            task_vertex.set_status(TaskStatus.RUNNING.value)

            cur_execution_result, next_executables = network.execute(task_vertex.id, messages)
            self.trace.set_subtasks(ctx.retrieve("sub_tasks"), 0)

            self.cur_execution.llm_messages = messages[len_message:]
            self.cur_execution.next_executors = next_executables

            # 更新 task_vertex 状态（成功运行收集结果）
            task_vertex.set_status(TaskStatus.SUCCESS.value)
            task_vertex.time_cost = self.cur_execution.time_cost
            for message in self.cur_execution.llm_messages:
                task_vertex.token += message.token_num
                task_vertex.token_cost += message.token_cost

            if task_vertex.id != "AgentNetworkPlannerGroup/AgentNetworkPlanner" and ctx.retrieve("step") is not None:
                ctx.register("step", ctx.retrieve("step") + 1)

            route = network.route
            targets = next_executables if next_executables else route.search(task_vertex.id)

            current_next_task_vertexes = []
            for target in targets:
                route.forward_message(task_vertex.id, target)
                if target != "COMPLETE":
                    vertex = network.get_vertex(target)
                    next_task_vertex = TaskVertex(vertex, ctx.retrieve("sub_tasks")[0]["task"])
                    next_task_vertex.type = get_task_type(vertex)
                    current_next_task_vertexes.append(next_task_vertex)

            self.trace.add_spans(task_vertex, current_next_task_vertexes, messages)
            current_third_party_next_task_vertexes = [ns for ns in current_next_task_vertexes if
                                                      isinstance(ns.executable, ThirdPartyVertex)]
            current_next_task_vertexes = [ns for ns in current_next_task_vertexes if
                                          not isinstance(ns.executable, ThirdPartyVertex)]
            third_party_next_task_vertexes.extend(current_third_party_next_task_vertexes)
            next_task_vertexes.extend(current_next_task_vertexes)

        except Exception as e:
            traceback.print_exc()
            self.release()
            raise Exception(e)
        if len(next_task_vertexes) > 0 or len(third_party_next_task_vertexes) > 0:
            return self._execute_graph(network, route, [task_vertex], next_task_vertexes,
                                       third_party_next_task_vertexes, organizeId=organizeId, max_step=1,
                                       need_summary=False)
        else:
            return ctx.retrieves_all()

    def _execute_graph(self,
                       network: Network,
                       route: Route,
                       father_task_vertexes: list[TaskVertex],
                       task_vertexes: list[TaskVertex],
                       third_party_task_vertexes: list[TaskVertex] = [],
                       params=None,
                       results=["result"],
                       organizeId=None,
                       need_summary=True):
        # 首先注册上下文
        if params:
            ctx.registers(params)
            
        while not self.task_manager.task_all_completed():
            
            # trace 相关
            if self.trace.level > 0:
                pre_level_route_front = self.trace.get_level_routes_front()
                
            # 获取当前需要执行的任务
            task_vertexes, third_party_task_vertexes = self.task_manager.get_cur_execution_tasks()
            
            # 向 trace 中添加节点
            adding_vertexes = [n.id for n in task_vertexes]
            adding_vertexes.extend([n.id for n in third_party_task_vertexes])
            self.trace.add_vertexes(adding_vertexes)
            
            # 判断图执行步数是否超限
            self.step += 1
            if self.step > self.max_step:
                self.release()
                # todo
                raise Exception("Max step reached, Task Failed!")
            
            # 执行三方节点任务
            if len(third_party_task_vertexes) > 0 and self.trace.level > 0:
                third_party_scheduler_executable = ThirdPartySchedulerExecutable(self.subtaskId, self.taskId, self,
                                                                                organizeId,
                                                                                pre_level_route_front)
                third_party_scheduler_executable.execute()
            
            # TODO 由感知层根据任务激活决定触发哪些 Agent，现在默认线性执行所有 TaskNode
            
            # 执行智能体网络节点任务
            for task in task_vertexes:
                try:
                    # 获取当前 agent 与大模型交互的历史上下文
                    messages = self.vertex_messages[task.executable.id]
                    len_message = len(messages)
                    
                    self.execution_history.append(History(pre_executors=self.task_manager.get_tasks(task.get_prev()), cur_executor=task))
                    self.cur_execution = self.execution_history[-1]
                    
                    # 开始运行 task
                    task.set_status(TaskStatus.RUNNING)
                    
                    # 如果是 subtask 列表中的新任务进来，需要能够根据之前执行完的subtasks构成的完整的执行图中恢复的上下文，自动填充当前subtask的executor需要的参数
                    route.match_context(task.executable.id)
                    cur_execution_result, next_tasks = network.execute(task.executable.id, messages)
                    
                    if task.executable.id == "AgentNetworkPlannerGroup/AgentNetworkPlanner":
                        sub_tasks = cur_execution_result.get("sub_tasks")
                        for sub_task in sub_tasks:
                            self.task_manager.add_task(sub_task["task"], network.get_vertex(sub_task["executor"]))
                            
                        for i in range(1, self.task_manager.task_cnt + 1):
                            if i != self.task_manager.task_cnt:
                                self.task_manager.task_queue[i].next = [i + 1]
                            if i != 1:
                                self.task_manager.task_queue[i].prev = [i - 1]

                    self.cur_execution.llm_messages = messages[len_message:]
                    self.cur_execution.next_tasks = next_tasks
                    
                    # task 运行成功，收集相关结果
                    task.set_status(TaskStatus.SUCCESS)
                    task.time_cost = self.cur_execution.time_cost
                    for message in self.cur_execution.llm_messages:
                        task.token += message.token_num
                        task.token_cost += message.token_cost

                    if task.executable.id != "AgentNetworkPlannerGroup/AgentNetworkPlanner" and ctx.retrieve(
                            "step") is not None:
                        ctx.register("step", ctx.retrieve("step") + 1)

                    # 搜索下一组任务
                    next_tasks = next_tasks or route.search(task, self.task_manager)
                    next_tasks_list = {}
                    for next_task in next_tasks:
                        if "id" not in next_task:
                            next_task["id"] = None
                        for k, v in next_task.items():
                            if k not in next_tasks_list:
                                next_tasks_list[k] = []
                            if k == "executor":
                                next_tasks_list[k].append(network.get_vertex(v))
                            else:
                                next_tasks_list[k].append(v)

                    # 把下一组任务注册到任务管理器中
                    if len(next_tasks_list) > 0:
                        self.task_manager.add_next_tasks(task, next_tasks_list.get("id"), next_tasks_list.get("task"), next_tasks_list.get("executor"))
                    # for next_task in next_tasks:
                    #     self.task_manager.add_next_task(task, next_task["task"], network.get_vertex(next_task["executor"]), task_id=next_task.get("id"))

                    next_task_vertexes, next_third_party_task_vertexes = self.task_manager.get_next_execution_tasks()
                    next_task_vertexes.extend(next_third_party_task_vertexes)
                    self.trace.add_spans(task, next_task_vertexes, messages)
                    
                    self.task_manager.refresh()
                except Exception as e:
                    self.release()
                    raise Exception(e)
        
        if need_summary:
            ctx.register("executionGraph", repr(self.trace))
            return self.summarize_result(network, route, task_vertexes,
                                         TaskVertex(
                                             network.get_vertex("AgentNetworkSummarizerGroup/AgentNetworkSummarizer"),
                                             "summarize the total progress of the execution graph"))
        else:
            return ctx.retrieves_all()

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
        task_vertex.set_status(TaskStatus.RUNNING.value)

        cur_execution_result, next_executables = network.execute(task_vertex.id, messages, **valuable_context)

        self.cur_execution.llm_messages = messages[len_message:]
        self.cur_execution.next_executors = next_executables

        # 更新 task_vertex 状态（成功运行收集结果）
        task_vertex.set_status(TaskStatus.SUCCESS.value)
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
