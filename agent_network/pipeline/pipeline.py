import uuid
import yaml

from agent_network.pipeline.history import History
from agent_network.network.graph import Graph
from agent_network.network.nodes.graph_node import GroupNode, AgentNode
from agent_network.network.route import Route
from agent_network.base import BaseAgentGroup
from agent_network.pipeline.task import TaskNode
import agent_network.pipeline.context as ctx


class Pipeline:
    def __init__(self, task, config, logger, id=None):
        self.task = task
        self.config = config
        self.logger = logger
        self.nodes = []
        self.step = 0
        if id is None:
            self.id = str(uuid.uuid4())
        else:
            self.id = id

        for item in self.config["context"]:
            if item["type"] == "str":
                ctx.register(item["name"], self.task if item["name"] == "task" else "")
            elif item["type"] == "list":
                ctx.register(item["name"], [])
        self.total_time = 0
        
        self.message_num = 0
        self.execution_history: list[History] = []
        self.cur_execution = None
        self.node_messages = dict()

        ctx.register_pipeline(id, self)

    def load_graph(self, graph: Graph):
        # 加载节点
        for group in self.config["group_pipline"]:
            group_config_path = list(group.values())[0]
            with open(group_config_path, "r", encoding="utf-8") as f:
                configs = yaml.safe_load(f)
                group = BaseAgentGroup(configs, self.logger)
                agents = group.load_agents()

                graph.add_node(group.name, GroupNode(group, group.params, group.results))
                for agent in agents:
                    graph.add_node(agent.name, AgentNode(agent, agent.params, agent.results))
                
                graph.add_route(group.name, group.start_agent, "start")
                for route in group.routes:
                    graph.add_route(route["source"], route["target"], route["type"])
        
        nodes = graph.get_nodes()
        for node in nodes:
            if system_message :=  graph.get_node(node).get_system_message():
                self.node_messages[node] = [system_message]
            else:
                self.node_messages[node] = []

    def load_route(self, graph: Graph, route: Route):
        for node_name, node_instance in graph.nodes.items():
            if not route.node_exist(node_name):
                route.register_node(node_name, node_instance.description)

        for item in graph.routes:
            route.register_contact(item["source"], item["target"], item["message_type"])
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
        self.step += 1
        max_step = self.config.get("max_step", 100)
        if self.step > max_step:
            self.release()
            raise Exception("Max step reached, Task Failed!")
        if context:
            ctx.registers(context)
        # TODO 由感知层根据任务激活决定触发哪些 Agent，现在默认线性执行所有 TaskNode
        next_nodes: list[TaskNode] = []
        for node in nodes:
            # todo 讨论是否需要合并message到上下文中
            messages = self.node_messages[node.name]
            try:
                len_message = len(messages)

                self.execution_history.append(History(pre_executors=father_nodes, cur_executor=node))
                self.cur_execution = self.execution_history[-1]

                messages, result, next_executables = graph.execute(node.name, messages)

                self.cur_execution.llm_messages = messages[len_message:]
                self.cur_execution.next_executors = next_executables
                
                # self.load_route(graph, route)
                if next_executables is None:
                    continue
                for next_executable in next_executables:
                    next_executable, message = route.forward_message(node.name, next_executable, result)
                    # if not leaf node
                    if message != "COMPLETE":
                        next_nodes.append(TaskNode(graph.get_node(next_executable), message))
            except Exception as e:
                self.release()
                raise Exception(e)
        
        self.execute_graph(graph, route, nodes, next_nodes)
        return ctx.retrieve_global_all()

    def register_time_cost(self, time_cost):
        self.total_time += time_cost

    def retrieve_result(self, key):
        return ctx.retrieve_global(key)

    def retrieve_results(self):
        return ctx.retrieve_global_all()

    def release(self):
        total_token_num = 0
        total_token_cost = 0
        total_time = self.total_time
        
        for execution in self.execution_history:
            for message in execution.llm_messages:
                total_token_num += message.token_num
                total_token_cost += message.token_cost
        
        self.logger.log("Agent-Network",
                        f"PIPELINE TOTSL TOKEN NUM: {total_token_num} COST: {total_token_cost}",
                        self.id)
        self.logger.log("Agent-Network", f"PIPELINE TIME COST TOTAL: {self.total_time}", self.id)
        self.logger.log("Agent-Network", f"PIPELINE: {self.id} has been released")
        ctx.release()
        ctx.release_global()
        self.total_time = 0

        self.message_num = 0
        self.execution_history: list[History] = []
        self.cur_execution = None
        self.node_messages = dict()

        return total_token_num, total_token_cost, total_time

