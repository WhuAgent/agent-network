import os

from agent_network.network.executable import Executable
import agent_network.graph.context as ctx
import threading
from agent_network.network.route import Route
from typing import Dict, List
from agent_network.entity.usage import UsageTime, UsageToken
from agent_network.network.vertexes.vertex import Vertex
from agent_network.network.vertexes.graph_vertex import GroupVertex, AgentVertex
from agent_network.base import BaseAgentGroup
from agent_network.network.vertexes.vertex import ThirdPartyVertex
from agent_network.network.vertexes.third_party.executable import ThirdPartyExecutable
from agent_network.utils.stats import *
import yaml
import json
import importlib
import asyncio


class Network(Executable):
    def __init__(self, id, description, params, results, logger):
        super().__init__(id, description)
        self.name = id
        self.params = params
        self.results = results
        self.num_vertexes = 0
        self.vertexes = {}
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
        self.third_party_vertexes = {}

    def load(self, config_path):
        with open(config_path, "r", encoding="UTF-8") as f:
            self.config = yaml.safe_load(f)

        def find_config_file(dir, target):
            for config_file in os.listdir(dir):
                if config_file[:config_file.rfind(".")] == target:
                    return config_file
            raise Exception(f"target: {target} load failed")

        group_dir = os.path.join("config", "group")
        agent_dir = os.path.join("config", "agent")
        link_dir = os.path.join("config", "link")
        for group_name in self.config["groups"]:
            group_config_path = os.path.join(group_dir, find_config_file(group_dir, group_name))
            if ".yaml" == group_config_path[-5:]:
                with open(group_config_path, "r", encoding="utf-8") as f:
                    configs = yaml.safe_load(f)
                    if "ref_id" in configs:
                        group = self.import_group(configs)
                    else:
                        group = BaseAgentGroup(self, self.route, configs, self.logger)
                    if "routes" in configs:
                        for route in configs["routes"]:
                            if group.start_agent is None and route["source"] == "start":
                                group.start_agent = route["target"]
                                self.add_route(group, group.id, route["target"], "hard")
                                break
                        for route in configs["routes"]:
                            if route["source"] == "start":
                                continue
                            self.add_route(group, route["source"], route["target"],
                                       route["rule"] if "rule" in route else "soft")
                    agents = group.load_agents(agent_dir, ".yaml")

                    self.add_vertex(group.id, GroupVertex(self, group, group.params, group.results))
                    for agent in agents:
                        self.add_vertex(group.id + "/" + agent.id, AgentVertex(self, agent, agent.params, agent.results, group.id))
                        # self.add_route(group, group_name, agent.id, "soft")

            elif ".json" == group_config_path[-5:]:
                with open(group_config_path, "r", encoding="utf-8") as f:
                    configs = json.load(f)
                    group = BaseAgentGroup(self, self.route, configs, self.logger)
                    self.add_vertex(group.id, GroupVertex(self, group, group.params, group.results))
                    for agent in configs["agents"]:
                        agent_file = find_config_file(agent_dir, agent)
                        agent_config_path = os.path.join(agent_dir, agent_file)
                        if agent_config_path[-5:] in [".json", ".yaml"]:
                            agent = group.load_agent(agent_dir, agent_file, agent)
                            self.add_vertex(group.id + "/" + agent.id, AgentVertex(self, agent, agent.params, agent.results, group.id))
                            # self.add_route(group, group_name, agent.id, "soft")
                    link_file = find_config_file(link_dir, group_name + "Link")
                    link_config_path = os.path.join(link_dir, link_file)
                    if link_config_path[-5:] in [".json", ".yaml"]:
                        with open(link_config_path, "r", encoding="utf-8") as f:
                            configs = json.load(f) if link_config_path[-5:] == ".json" else yaml.safe_load(f)
                            if configs["group"] != group_name:
                                raise Exception(f"links' group match failed: {link_config_path}")
                            for link in configs["links"]:
                                if link["source"] == "start":
                                    group.start_agent = link["target"]
                                    self.add_route(group, group.id, link["target"], "hard")
                                    break
                            for link in configs["links"]:
                                if link["source"] == "start":
                                    continue
                                self.add_route(group, link["source"], link["target"], link["type"])
            # for route in self.routes:
            #     if route["source"] != "start" and route["source"] not in group.agents.keys():
            #         raise Exception(
            #             f"group: {group_name}, link: source-{route['source']}-target-{route['target']} illegal.")
        for client in self.clients:
            asyncio.get_event_loop().run_until_complete(client.register(self.vertexes.values()))
        self.refresh_vertexes_from_clients()
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
        for vertex_name, vertex_instance in self.vertexes.items():
            if not self.route.vertex_exist(vertex_name):
                self.route.register_vertex(vertex_name, vertex_instance.description)

        for item in self.routes:
            if item["source"] == "start" or item["target"] == "end": continue
            if item["rule"] is None:
                item["rule"] = "soft"
            self.route.register_contact(item["source"], item["target"],
                                        item["rule"])

    def execute(self, vertex, messages, **kwargs):
        current_ctx = ctx.retrieve_global_all()
        ctx.shared_context(current_ctx)
        if vertex not in self.vertexes:
            raise Exception(f'vertex: {vertex} is absent from graph')
        result, next_executables = self.vertexes.get(vertex).execute(messages, **kwargs)
        ctx.registers_global(ctx.retrieves([result["name"] for result in self.results] if self.results else []))
        return result, next_executables

    def add_vertex(self, name, vertex: Executable):
        if name not in self.vertexes:
            self.vertexes[name] = vertex
            self.num_vertexes += 1
            if isinstance(vertex, GroupVertex):
                self.current_groups_name.append(name)
            if isinstance(vertex, ThirdPartyVertex) and isinstance(vertex.executable, ThirdPartyExecutable):
                third_party_vertex_key = vertex.executable.service_group + '&&' + vertex.executable.service_name + '&&' + vertex.name
                self.third_party_vertexes[third_party_vertex_key] = vertex
            self.logger.log("Agent-Network-Graph",
                            f"VERTEX: {name} TYPE: {type(vertex).__name__} has been added to the graph", self.name)

    def remove_vertex(self, name, release=False):
        # TODO NEED OPTIMIZE
        removed_vertexes = []
        if name in self.vertexes:
            # TODO 删除三方节点
            vertex = self.get_vertex(name)
            if isinstance(vertex, GroupVertex):
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
                for agent_name in vertex.executable.agents.keys():
                    agent_vertex = self.get_vertex(agent_name)
                    agent_usages_token = None
                    agent_usages_time = None
                    if agent_vertex is not None:
                        agent_usages_token, agent_usages_time = self.get_vertex(agent_name).release()
                        if agent_name in vertex.executable.current_agents_name:
                            vertex.executable.remove_agent(agent_name)
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
                            self.logger.log("Agent-Network-Graph",
                                            f"AGENT: {agent_name} TOKEN TOTAL: {usage_token_total_map}", self.name)
                            self.logger.log("Agent-Network-Graph", f"AGENT: {agent_name} TIME COST TOTAL: {total_time}",
                                            self.name)
                            self.logger.log("Agent-Network-Graph", f"AGENT: {agent_name} has been removed", self.name)
                            self.remove_common(agent_name)
                            removed_vertexes.append(agent_name)
                    else:
                        if agent_name in self.agents_usages_time_history and agent_name in self.agents_usages_token_history:
                            agent_usages_token = self.agents_usages_token_history[agent_name]
                            agent_usages_time = self.agents_usages_time_history[agent_name]
                    if agent_usages_token is not None and agent_usages_time is not None:
                        for group_agent in vertex.executable.agents[agent_name]:
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
                self.remove_common(name)
            elif isinstance(vertex, AgentVertex):
                for group in self.current_groups_name:
                    group_vertex = self.get_vertex(group)
                    group_vertex.executable.remove_agent_if_exist(name)
                agent_usages_token, agent_usages_time = vertex.release()
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
            elif isinstance(vertex, ThirdPartyVertex) and not release:
                raise Exception(f"can not remove third party vertex: {name}")
            removed_vertexes.append(name)
            self.logger.log("Agent-Network-Graph",
                            f"VERTEX: {name} TYPE: {type(vertex).__name__} has been removed from the graph", self.name)
            return removed_vertexes

    def remove_common(self, name):
        del self.vertexes[name]
        self.num_vertexes -= 1
        self.routes = [route for route in self.routes if route["source"] != name and route["target"] != name]
        self.route.deregister_vertex(name)

    def get_vertex(self, name) -> Vertex | None:
        if name in self.vertexes:
            return self.vertexes[name]
        return None

    def get_vertexes(self) -> list[Executable]:
        return list(self.vertexes.keys())

    def vertex_exists(self, name):
        return name in self.vertexes

    def add_route(self, group, source, target, rule):
        if source != group.id and source != "start" and source not in group.agents.keys() or (source == group.id and target != group.start_agent):
            raise Exception(
                f"group: {group.id}, link: source-{source}-target-{target} illegal.")
        self.routes.append({
            "source": source,
            "target": target,
            "rule": rule
        })

    def release(self):
        total_removed_vertexes = []
        for vertex in list(self.vertexes.keys()):
            if vertex in total_removed_vertexes:
                continue
            removed_vertexes = self.remove_vertex(vertex, True)
            total_removed_vertexes.extend(removed_vertexes)
        self.logger.log("Agent-Network-Graph", f"GRAPH TOKEN TOTAL: {self.usage_token_total_map}", self.name)
        self.logger.log("Agent-Network-Graph", f"GRAPH TIME COST TOTAL: {self.total_time}", self.name)
        self.logger.log("Agent-Network-Graph", f"GRAPH: {self.name} has been released", self.name)
        self.vertexes = {}
        self.routes = []
        self.num_vertexes = 0
        for client in self.clients:
            client.release()
        return self.usage_token_total_map, self.total_time

    def refresh_vertexes_from_clients(self):
        for client in self.clients:
            client.update_all_services_vertexes()

    def register_clients(self, clients):
        self.clients.extend(clients)

    def refresh_third_party_vertexes(self, service_name, service_group, vertexes):
        third_party_vertex_key_prefix = service_group + '&&' + service_name
        third_party_exist_vertexes = [third_party_exist_vertex for third_party_exist_vertex in
                                      self.third_party_vertexes.keys() if
                                      third_party_vertex_key_prefix in third_party_exist_vertex]
        for vertex in vertexes:
            if not self.vertex_exists(vertex.id):
                self.add_vertex(vertex.id, vertex)
            else:
                third_party_exist_vertexes.remove(third_party_vertex_key_prefix + '&&' + vertex.id)
        for third_party_exist_vertex in third_party_exist_vertexes:
            self.remove_third_party_vertex(service_name, service_group, third_party_exist_vertex.split['&&'][2])

    def remove_third_party_vertexes(self, service_name, service_group):
        third_party_vertex_key_prefix = service_group + '&&' + service_name
        for third_party_vertex in list(self.third_party_vertexes.keys()):
            if third_party_vertex_key_prefix in third_party_vertex:
                del self.third_party_vertexes[third_party_vertex]
                # self.remove_common(third_party_vertex.split('&&')[2])
                del self.vertexes[third_party_vertex.split('&&')[2]]
                self.num_vertexes -= 1
                self.logger.log("Agent-Network-Graph",
                                f"VERTEX: {third_party_vertex} TYPE: ThirdPartyNode has been removed from the graph",
                                self.name)

    def remove_third_party_vertex(self, service_name, service_group, name):
        third_party_vertex_key = service_group + '&&' + service_name + '&&' + name
        if third_party_vertex_key in list(self.third_party_vertexes.keys()):
            del self.third_party_vertexes[third_party_vertex_key]
            # self.remove_common(name)
            del self.vertexes[name]
            self.num_vertexes -= 1
            self.logger.log("Agent-Network-Graph",
                            f"VERTEX: {third_party_vertex_key} TYPE: ThirdPartyNode has been removed from the graph",
                            self.name)


# TODO 基于感知层去调度graph及其智能体
class GraphStart:
    def __init__(self, network: Network):
        self.network = network

    def execute(self, start_vertexes):
        for start_vertex in start_vertexes:
            assert start_vertex in self.network.vertexes, f"vertexes: {start_vertex} is not in graph: {self.network.name}"
        start_vertexes = [self.network.vertexes[start_vertex] for start_vertex in start_vertexes]
        vertexes_threads = []
        for start_vertex in start_vertexes:
            current_ctx = ctx.retrieve_global_all()
            vertex_thread = threading.Thread(
                target=lambda sv=start_vertex: (
                    ctx.shared_context(current_ctx),
                    sv.execute(),
                    ctx.registers_global(
                        ctx.retrieves(
                            [result["name"] for result in self.network.results] if self.network.results else []))
                )
            )
            vertexes_threads.append(vertex_thread)

        for vertex_thread in vertexes_threads:
            vertex_thread.start()
        for vertex_thread in vertexes_threads:
            vertex_thread.join()

    def add_vertex(self, name, vertex):
        self.network.add_vertex(name, vertex)

    def get_vertex(self, name):
        return self.network.get_vertex(name)
