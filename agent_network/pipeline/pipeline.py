import uuid
import traceback

from agent_network.pipeline.history import History
from agent_network.network.graph import Graph
from agent_network.network.route import Route
from agent_network.pipeline.task import TaskNode
import agent_network.pipeline.context as ctx
from agent_network.pipeline.trace import Trace


class Pipeline:
    def __init__(self, task, logger, id=None):
        self.task = task
        self.logger = logger
        self.nodes = []
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
        self.node_messages = dict()

        ctx.register_pipeline(id, self)

    # def load_graph(self, graph: Graph):
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
    #             graph.add_node(group.name, GroupNode(graph, group, group.params, group.results))
    #             for agent in agents:
    #                 graph.add_node(agent.name, AgentNode(graph, agent, agent.params, agent.results, group.name))
    #
    #             graph.add_route(group.name, group.name, group.start_agent, "start", "hard")
    #             for route in group.routes:
    #                 if "rule" not in route:
    #                     route["rule"] = "soft"
    #                 graph.add_route(group.name, route["source"], route["target"], route["type"], route["rule"])
    #
    #     nodes = graph.get_nodes()
    #     # TODO 分布式下如何处理node_messages
    #     for node in nodes:
    #         if system_message := graph.get_node(node).get_system_message():
    #             self.node_messages[node] = [system_message]
    #         else:
    #             self.node_messages[node] = []
    #     graph.refresh_nodes_from_clients()
    #     graph.load_route()

    # def import_group(self, graph, group_config):
    #     if "load_type" in group_config and group_config["load_type"] == "module":
    #         group_module = importlib.import_module(group_config["loadModule"])
    #         group_class = getattr(group_module, group_config["loadClass"])
    #         group_instance = group_class(graph, graph.route, group_config, self.logger)
    #     else:
    #         raise Exception("Group load type must be module!")
    #     return group_instance

    def execute(self, graph: Graph, task: str, start_node, context=None):
        try:
            nodes = graph.get_nodes()
            # TODO 分布式下如何处理node_messages
            for node in nodes:
                if system_message := graph.get_node(node).get_system_message():
                    self.node_messages[node] = [system_message]
                else:
                    self.node_messages[node] = []
            return self._execute_graph(graph,
                                       graph.route,
                                       [TaskNode(name="start")],
                                       [TaskNode(graph.get_node(start_node), task)],
                                       context)
        except Exception as e:
            traceback.print_exc()
            self.release()
            raise Exception(e)

    def _execute_graph(self,
                       graph: Graph,
                       route: Route,
                       father_nodes: list[TaskNode],
                       nodes: list[TaskNode],
                       context=None):
        if nodes is None or len(nodes) == 0:
            return
        self.trace.add_nodes([n.name for n in nodes])
        self.step += 1
        # max_step = self.config.get("max_step", 100)
        max_step = 100
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
                        next_task_node = TaskNode(graph.get_node(next_executable), message)
                        next_nodes.append(next_task_node)
                self.trace.add_spans(node.name, [nn for nn in next_executables], messages, result)
            except Exception as e:
                self.release()
                raise Exception(e)

        self._execute_graph(graph, route, nodes, next_nodes)
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
        self.node_messages = dict()

        return total_token_num, total_token_cost, total_time
