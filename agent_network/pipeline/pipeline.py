import importlib
import uuid
import yaml

from agent_network.pipeline.history import History
from agent_network.network.graph import Graph
from agent_network.network.nodes.graph_node import GroupNode, AgentNode
from agent_network.network.route import Route
from agent_network.base import BaseAgentGroup
from agent_network.pipeline.task import TaskNode
import agent_network.pipeline.new_context.local as ctx
from agent_network.pipeline.trace import Trace

from agent_network.pipeline.new_context.base import BaseContext
from agent_network.utils.llm.message import UserMessage


class Pipeline:
    def __init__(self, task, config, logger, context=BaseContext, id=None):
        self.task = task
        self.config = config
        self.logger = logger
        
        # 记录 pipeline 执行的步数
        self.step = 0

        # 为 pipeline 分配 id
        self.id = id if id else str(uuid.uuid4())
        self.trace = Trace(self.id)
        
        # 上下文初始化
        self.config["context"] = self.config.get("context") or []
        context_map = {}
        for item in self.config.get("context"):
            if item["type"] == "str":
                context_map[item["name"]] = self.task if item["name"] == "task" else ""
            elif item["type"] == "list":
                context_map[item["name"]] = []
        ctx.init(context, self.logger, **context_map)
        # self.total_time = 0

        # self.message_num = 0
        # self.execution_history: list[History] = []
        # self.cur_execution = None
        # self.node_messages = dict()

        # ctx.register_pipeline(id, self)

    def load_graph(self, graph: Graph):
        # 加载节点
        for group in self.config["group_pipline"]:
            group_config_path = list(group.values())[0]
            with open(group_config_path, "r", encoding="utf-8") as f:
                configs = yaml.safe_load(f)
                if configs.get("load_type") == "module":
                    group_module = importlib.import_module(configs["loadModule"])
                    group_class = getattr(group_module, configs["loadClass"])
                    group = group_class(configs, self.logger)
                else:
                    group = BaseAgentGroup(configs, self.logger)
                agents = group.load_agents()

                graph.add_node(group.name, GroupNode(group, group.params, group.results))
                for agent in agents:
                    graph.add_node(agent.name, AgentNode(agent, agent.params, agent.results))

                if group.start_agent:
                    graph.add_route(group.name, group.start_agent, "start")
                for route in group.routes:
                    if "type" in route:
                        route["message_type"] = route["type"]
                        del route["type"]
                    graph.add_route(**route)

        nodes = graph.get_nodes()
        for node in nodes:
            if system_message := graph.get_node(node).get_system_message():
                ctx.register_message(node, system_message)

    def load_route(self, graph: Graph, route: Route):
        for node_name, node_instance in graph.nodes.items():
            if not route.node_exist(node_name):
                route.register_node(node_name, node_instance.description)

        for item in graph.routes:
            route.register_contact(item.get("source"), item.get("target"), item.get("message_type"), item.get("message_group"))
        graph.route = route

    def load(self, graph: Graph, route: Route):
        if self.step == 0:
            self.load_graph(graph)
            self.load_route(graph, route)

    def execute(self, graph: Graph, route: Route, task: str, context=None):
        self.load(graph, route)
        return self.execute_graph(graph,
                                  route,
                                  [TaskNode(name="start")],
                                  [TaskNode(graph.get_node(self.config["start_node"]), task)],
                                  context,
                                  True)

    def execute_graph(self,
                      graph: Graph,
                      route: Route,
                      father_nodes: list[TaskNode],
                      nodes: list[TaskNode],
                      context=None,
                      skip_load=False):
        if not skip_load:
            self.load(graph, route)
        if nodes is None or len(nodes) == 0:
            return
        self.trace.add_nodes([n.name for n in nodes])
        self.step += 1
        max_step = self.config.get("max_step", -1)
        if max_step > 0 and self.step > max_step:
            self.release()
            raise Exception("Max step reached, Task Failed!")
        if context:
            ctx.registers(context)
        # TODO 由感知层根据任务激活决定触发哪些 Agent，现在默认线性执行所有 TaskNode
        next_nodes: list[TaskNode] = []
        for node in nodes:
            # todo 讨论是否需要合并message到上下文中
            messages = ctx.execute("retrieve_messages", node=node.name)
            try:
                len_message = len(messages)

                # 先把当前得 execution 注册到上下文中
                ctx.register_execution_history(History(pre_executors=father_nodes, cur_executor=node))
                cur_execution: History = ctx.retrieve_cur_execution()

                # 执行 node 的 forward 逻辑
                messages, result, next_executables = graph.execute(node.name, messages)

                # 更新 execution 信息并回写到上下文
                if messages:
                    cur_execution.llm_messages = messages[len_message:]
                    cur_execution.next_executors = next_executables
                    ctx.update_cur_execution(cur_execution)

                # 判断当前 node 有没有接下来需要执行的 node
                if next_executables is None:
                    continue
                for next_executable in next_executables:
                    next_executable, message = route.forward_message(node.name, next_executable, messages)
                    # if not leaf node
                    if next_executable and message != "COMPLETE":
                        next_task_node = TaskNode(graph.get_node(next_executable), message=UserMessage(message))
                        next_nodes.append(next_task_node)
                self.trace.add_spans(node.name, [nn for nn in next_executables], messages, result)
            except Exception as e:
                self.release()
                raise Exception(e)

        self.execute_graph(graph, route, nodes, next_nodes)
        return ctx.retrieve_all()

    def register_time_cost(self, time_cost):
        self.total_time += time_cost

    def retrieve_result(self, key):
        return ctx.retrieve_global(key)

    def retrieve_results(self):
        return ctx.retrieve_global_all()

    def release(self):
        total_token_num, total_token_cost, total_time = ctx.summary()

        self.logger.log("network", 
                        f"PIPELINE {self.id} TOTSL TOKEN NUM: {total_token_num} COST: {total_token_cost}",
                        "Agent-Network")
        self.logger.log("network", 
                        f"PIPELINE {self.id} TIME COST TOTAL: {total_time}", 
                        "Agent-Network")
        self.logger.log("network", 
                        f"PIPELINE {self.id} has been released", 
                        "Agent-Network")
        
        self.logger.categorize_log()
        self.logger.log_trace(self.trace)

        ctx.release()
        ctx.release_global()

        # self.total_time = 0

        # self.message_num = 0
        # self.execution_history: list[History] = []
        # self.cur_execution = None
        # self.node_messages = dict()

        return total_token_num, total_token_cost, total_time
