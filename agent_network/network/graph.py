from agent_network.network.executable import Executable
import agent_network.pipeline.context as ctx
import threading
from agent_network.network.route import Route
from typing import Dict, List
from agent_network.entity.usage import UsageTime, UsageToken
from agent_network.network.nodes.node import Node
from agent_network.network.nodes.graph_node import GroupNode, AgentNode
from agent_network.base import BaseAgentGroup
from agent_network.network.nodes.node import ThirdPartyNode
from agent_network.network.nodes.third_party.executable import ThirdPartyExecutable
from agent_network.utils.stats import *
import yaml
import importlib
import asyncio


class Graph(Executable):
    def __init__(self, name, task, description, start_node, params, results, logger):
        super().__init__(name, task, description)
        self.name = name
        self.task = task

        self.params = params
        self.results = results

        self.num_nodes = 0
        self.start_node = start_node

        self.nodes = {}
        self.routes = []
        self.route = None
        self.total_time = 0
        self.usage_token_total_map = {"completion_tokens": 0, "prompt_tokens": 0, "total_tokens": 0,
                                      "completion_cost": 0, "prompt_cost": 0, "total_cost": 0}
        self.logger = logger
        self.current_groups_name = []
        self.agents_usages_time_history: Dict[str, List[UsageTime]] = {}
        self.agents_usages_token_history: Dict[str, List[UsageToken]] = {}

        self.clients = []
        self.third_party_nodes = {}

    def load(self, config_path):
        with open(config_path, "r", encoding="UTF-8") as f:
            self.config = yaml.safe_load(f)
        # 加载节点
        for group in self.config["group_pipline"]:
            group_config_path = list(group.values())[0]
            with open(group_config_path, "r", encoding="utf-8") as f:
                configs = yaml.safe_load(f)
                if "ref_id" in configs:
                    group = self.import_group(configs)
                else:
                    group = BaseAgentGroup(self, self.route, configs, self.logger)
                agents = group.load_agents()

                self.add_node(group.name, GroupNode(self, group, group.params, group.results))
                for agent in agents:
                    self.add_node(agent.name, AgentNode(self, agent, agent.params, agent.results, group.name))

                self.add_route(group.name, group.name, group.start_agent, "start", "hard")
                for route in group.routes:
                    if "rule" not in route:
                        route["rule"] = "soft"
                    self.add_route(group.name, route["source"], route["target"], route["type"], route["rule"])
        for client in self.clients:
            asyncio.get_event_loop().run_until_complete(client.register(self.nodes.values()))
        self.refresh_nodes_from_clients()
        self.load_route()

    def import_group(self, group_config):
        if "load_type" in group_config and group_config["load_type"] == "module":
            group_module = importlib.import_module(group_config["loadModule"])
            group_class = getattr(group_module, group_config["loadClass"])
            group_instance = group_class(self, self.route, group_config, self.logger)
        else:
            raise Exception("Group load type must be module!")
        return group_instance

    def load_route(self):
        self.route = Route()
        for node_name, node_instance in self.nodes.items():
            if not self.route.node_exist(node_name):
                self.route.register_node(node_name, node_instance.description)

        for item in self.routes:
            if item["rule"] is None:
                item["rule"] = "soft"
            self.route.register_contact(item["group"], item["source"], item["target"], item["message_type"], item["rule"])

    def execute(self, node, messages, **kwargs):
        current_ctx = ctx.retrieve_global_all()
        ctx.shared_context(current_ctx)
        if node not in self.nodes:
            raise Exception(f'node: {node} is absent from graph')
        messages, result, next_executables = self.nodes.get(node).execute(messages, **kwargs)
        # TODO 通过路由自动search来找next_executables或者过滤next_executables
        ctx.registers_global(ctx.retrieves([result["name"] for result in self.results] if self.results else []))
        return messages, result, next_executables

    def add_node(self, name, node: Executable):
        if name not in self.nodes:
            self.nodes[name] = node
            self.num_nodes += 1
            if isinstance(node, GroupNode):
                self.current_groups_name.append(name)
            if isinstance(node, ThirdPartyNode) and isinstance(node.executable, ThirdPartyExecutable):
                third_party_node_key = node.executable.service_group + '-' + node.executable.service_name + '-' + node.name
                self.third_party_nodes[third_party_node_key] = node

    def remove_node(self, name):
        # TODO NEED OPTIMIZE
        removed_nodes = []
        if name in self.nodes:
            # TODO 删除三方节点
            node = self.get_node(name)
            if isinstance(node, GroupNode):
                total_usage = {
                    "completion_tokens": 0,
                    "prompt_tokens": 0,
                    "total_tokens": 0,
                    "completion_cost": 0,
                    "prompt_cost": 0,
                    "total_cost": 0
                }
                total_time = 0
                self.current_groups_name.remove(name)
                # 若强绑定group和agent的生命周期
                # 拿曾经拥有过的agent的所有统计数据，输出该group最终的
                for agent_name in node.executable.agents.keys():
                    agent_node = self.get_node(agent_name)
                    agent_usages_token = None
                    agent_usages_time = None
                    if agent_node is not None:
                        agent_usages_token, agent_usages_time = self.get_node(agent_name).release()
                        if agent_name in node.executable.current_agents_name:
                            node.executable.remove_agent(agent_name)
                            usage_token_total_map, total_time = usage_calculate_all(agent_usages_token,
                                                                                    agent_usages_time)
                            self.usage_token_total_map["completion_tokens"] += usage_token_total_map[
                                "completion_tokens"]
                            self.usage_token_total_map["prompt_tokens"] += usage_token_total_map["prompt_tokens"]
                            self.usage_token_total_map["total_tokens"] += usage_token_total_map["total_tokens"]
                            self.usage_token_total_map["completion_cost"] += usage_token_total_map["completion_cost"]
                            self.usage_token_total_map["prompt_cost"] += usage_token_total_map["prompt_cost"]
                            self.usage_token_total_map["total_cost"] += usage_token_total_map["total_cost"]
                            self.total_time += total_time
                            self.agents_usages_time_history[agent_name] = agent_usages_time
                            self.agents_usages_token_history[agent_name] = agent_usages_token
                            self.logger.log("Agent-Network-Graph", f"AGENT: {agent_name} TOKEN TOTAL: {usage_token_total_map}", self.name)
                            self.logger.log("Agent-Network-Graph", f"AGENT: {agent_name} TIME COST TOTAL: {total_time}", self.name)
                            self.logger.log("Agent-Network-Graph", f"AGENT: {agent_name} has been removed", self.name)
                            self.remove_common(agent_name)
                            removed_nodes.append(agent_name)
                    else:
                        if agent_name in self.agents_usages_time_history and agent_name in self.agents_usages_token_history:
                            agent_usages_token = self.agents_usages_token_history[agent_name]
                            agent_usages_time = self.agents_usages_time_history[agent_name]
                    if agent_usages_token is not None and agent_usages_time is not None:
                        for group_agent in node.executable.agents[agent_name]:
                            if group_agent.end_timestamp == group_agent.begin_timestamp:
                                group_agent.separate()
                            agent_total_usage, agent_total_time = usage_calculate(agent_usages_token, agent_usages_time,
                                                                                  group_agent.begin_timestamp,
                                                                                  group_agent.end_timestamp)
                            total_usage['completion_tokens'] += agent_total_usage['completion_tokens']
                            total_usage['prompt_tokens'] += agent_total_usage['prompt_tokens']
                            total_usage['total_tokens'] += agent_total_usage['total_tokens']
                            total_usage['completion_cost'] += agent_total_usage['completion_cost']
                            total_usage['prompt_cost'] += agent_total_usage['prompt_cost']
                            total_usage['total_cost'] += agent_total_usage['total_cost']
                            total_time += agent_total_time
                self.logger.log("Agent-Network-Graph", f"GROUP: {name} TOKEN TOTAL: {total_usage}", self.name)
                self.logger.log("Agent-Network-Graph", f"GROUP: {name} TIME COST TOTAL: {total_time}", self.name)
                self.logger.log("Agent-Network-Graph", f"GROUP: {name} has been removed from graph {self.name}",
                                self.name)
            elif isinstance(node, AgentNode):
                for group in self.current_groups_name:
                    group_node = self.get_node(group)
                    group_node.executable.remove_agent_if_exist(name)
                agent_usages_token, agent_usages_time = node.release()
                self.agents_usages_time_history[name] = agent_usages_time
                self.agents_usages_token_history[name] = agent_usages_token
                usage_token_total_map, total_time = usage_calculate_all(agent_usages_token, agent_usages_time)
                self.usage_token_total_map["completion_tokens"] += usage_token_total_map["completion_tokens"]
                self.usage_token_total_map["prompt_tokens"] += usage_token_total_map["prompt_tokens"]
                self.usage_token_total_map["total_tokens"] += usage_token_total_map["total_tokens"]
                self.usage_token_total_map["completion_cost"] += usage_token_total_map["completion_cost"]
                self.usage_token_total_map["prompt_cost"] += usage_token_total_map["prompt_cost"]
                self.usage_token_total_map["total_cost"] += usage_token_total_map["total_cost"]
                self.total_time += total_time
                self.logger.log("Agent-Network-Graph", f"AGENT: {name} TOKEN TOTAL: {usage_token_total_map}", self.name)
                self.logger.log("Agent-Network-Graph", f"AGENT: {name} TIME COST TOTAL: {total_time}", self.name)
                self.logger.log("Agent-Network-Graph", f"AGENT: {name} has been removed from graph {self.name}",
                                self.name)
            self.remove_common(name)
            removed_nodes.append(name)
            self.logger.log("Agent-Network-Graph", f"NODE: {name} has been removed from graph: {self.name}", self.name)
            return removed_nodes

    def remove_common(self, name):
        del self.nodes[name]
        self.num_nodes -= 1
        self.routes = [route for route in self.routes if route["source"] != name and route["target"] != name]
        self.route.deregister_node(name)

    def get_node(self, name) -> Node | None:
        if name in self.nodes:
            return self.nodes[name]
        return None

    def get_nodes(self) -> list[Executable]:
        return list(self.nodes.keys())

    def node_exists(self, name):
        return name in self.nodes

    def add_route(self, group, source, target, message_type, rule):
        self.routes.append({
            "group": group,
            "source": source,
            "target": target,
            "message_type": message_type,
            "rule": rule
        })

    def release(self):
        total_removed_nodes = []
        for node in list(self.nodes.keys()):
            if node in total_removed_nodes:
                continue
            removed_nodes = self.remove_node(node)
            total_removed_nodes.extend(removed_nodes)
        self.logger.log("Agent-Network-Graph", f"GRAPH TOKEN TOTAL: {self.usage_token_total_map}", self.name)
        self.logger.log("Agent-Network-Graph", f"GRAPH TIME COST TOTAL: {self.total_time}", self.name)
        self.logger.log("Agent-Network-Graph", f"GRAPH: {self.name} has been released", self.name)
        self.nodes = {}
        self.routes = []
        self.num_nodes = 0
        for client in self.clients:
            client.release()
        return self.usage_token_total_map, self.total_time

    def refresh_nodes_from_clients(self):
        for client in self.clients:
            client.update_all_services_nodes()

    def register_clients(self, clients):
        self.clients.extend(clients)

    def refresh_third_party_nodes(self, service_name, service_group, nodes):
        third_party_node_key_prefix = service_group + '-' + service_name
        third_party_exist_nodes = [third_party_exist_node for third_party_exist_node in self.third_party_nodes.keys() if third_party_node_key_prefix in third_party_exist_node]
        for node in nodes:
            if not self.node_exists(node.name):
                self.add_node(node.name, node.executable)
            third_party_exist_nodes.remove(third_party_node_key_prefix + '-' + node.name)
        for third_party_exist_node in third_party_exist_nodes:
            self.remove_third_party_node(service_name, service_group, third_party_exist_node.split['-'][2])

    def remove_third_party_nodes(self, service_name, service_group):
        third_party_node_key_prefix = service_group + '-' + service_name
        for third_party_node in self.third_party_nodes.keys():
            if third_party_node_key_prefix in third_party_node:
                del self.third_party_nodes[third_party_node]
                self.remove_common(third_party_node.split['-'][2])

    def remove_third_party_node(self, service_name, service_group, name):
        third_party_node_key = service_group + '-' + service_name + '-' + name
        if third_party_node_key in self.third_party_nodes:
            del self.third_party_nodes[third_party_node_key]
            self.remove_common(name)


# TODO 基于感知层去调度graph及其智能体
class GraphStart:
    def __init__(self, graph: Graph):
        self.graph = graph

    def execute(self, start_nodes, task):
        for start_node in start_nodes:
            assert start_node in self.graph.nodes, f"nodes: {start_node} is not in graph: {self.graph.name}"
        start_nodes = [self.graph.nodes[start_agent] for start_agent in start_nodes]
        nodes_threads = []
        for start_node in start_nodes:
            current_ctx = ctx.retrieve_global_all()
            node_thread = threading.Thread(
                target=lambda ne=start_node, ic=task if not task else self.graph.task: (
                    ctx.shared_context(current_ctx),
                    ne.execute(ic),
                    ctx.registers_global(
                        ctx.retrieves([result["name"] for result in self.graph.results] if self.graph.results else []))
                )
            )
            nodes_threads.append(node_thread)

        for node_thread in nodes_threads:
            node_thread.start()
        for node_thread in nodes_threads:
            node_thread.join()

    def add_node(self, name, node):
        self.graph.add_node(name, node)

    def get_node(self, name):
        return self.graph.get_node(name)
