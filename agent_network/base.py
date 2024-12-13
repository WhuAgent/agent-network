import importlib
import json
from agent_network.utils.openai_llm import chat_llm, Usage
from agent_network.network.graph import Graph
from agent_network.network.nodes.graph_node import AgentNode
from datetime import datetime
import yaml
from agent_network.network.executable import Executable
from abc import abstractmethod
import agent_network.pipeline.context as ctx
from agent_network.entity.usage import UsageToken, UsageTime
from agent_network.entity.group_agent import GroupAgent
from typing import List, Dict


class BaseAgent(Executable):

    def __init__(self, config, logger):
        super().__init__(config["name"], config["task"], config["description"])
        self.config = config
        self.task = self.config["task"]
        self.title = self.config["name"]
        self.description = self.config["description"]
        self.class_name = self.config["ref_id"]
        self.role = self.config["role"]
        self.description = self.config["description"]

        self.params = self.config["params"]
        self.results = self.config["results"]

        self.model = self.config["model"]
        self.prompts = self.config.get("prompts")
        self.tools = self.config.get("tools")
        self.logger = logger
        self.if_error = False
        self.error = None
        self.history_action = []
        self.append_history_num = 0
        if "append_history_num" in self.config:
            self.append_history_num = self.config["append_history_num"]
        self.keep_history_num = 0
        if "keep_history_num" in self.config:
            self.keep_history_num = self.config["keep_history_num"]
        if self.append_history_num > self.keep_history_num:
            raise Exception("append history number can not be more than keep history number")
        self.runtime_revision_number = 0
        self.cost_history = []
        self.usages: List[UsageToken] = []
        self.time_costs: List[UsageTime] = []

        self.system_message = self.initial_messages()

    def add_message(self, role, content, messages=None):
        if messages is None:
            messages = []
        if not (len(messages) > 0 and messages[0]["role"] == "system"):
            messages.insert(0, self.system_message)
            self.log("system", self.system_message["content"], self.__class__.__name__)
        messages.append({
            "role": role,
            "content": content
        })
        self.log(role, content)
        if self.append_history_num > 0:
            for i in range(min(self.append_history_num, len(self.history_action))):
                messages.append({"role": "system", "content": f"The {i + 1}th historical records:\n"})
                history_action = self.history_action[len(self.history_action) - self.append_history_num + i]
                messages.append({"role": history_action["role"], "content": history_action["content"]})
        return messages

    def initial_messages(self):
        pass

    @abstractmethod
    def forward(self, message, **kwargs):
        results = dict()
        return results

    def execute(self, current_task, **kwargs):
        begin_t = datetime.now().timestamp()
        results = self.forward(current_task, **kwargs)
        end_t = datetime.now().timestamp()
        self.log("Agent-Network", f"{self.name} time cost: {end_t - begin_t}", self.name)
        time_cost = end_t - begin_t
        self.time_costs.append(UsageTime(begin_t, time_cost))
        ctx.register_time(self.name, time_cost)
        return results

    def chat_llm(self, messages):
        # todo 该时间不精准，应该取execute的开始时间
        time_chat_begin = datetime.now().timestamp()
        response, usage = chat_llm(messages)
        usage_token_map = {'completion_tokens': usage.completion_tokens, 'prompt_tokens': usage.prompt_tokens,
                           'total_tokens': usage.total_tokens, 'total_cost': usage.total_cost,
                           'completion_cost': usage.completion_cost, 'prompt_cost': usage.prompt_cost}
        self.usages.append(UsageToken(time_chat_begin, usage_token_map))
        ctx.register_usage(usage_token_map)
        self.log("Agent-Network", f"TOKEN STEP: {usage_token_map}", self.name)
        if len(self.history_action) >= self.keep_history_num:
            self.history_action.pop(0)
        self.history_action.append({"role": response.role, "content": str(response.content)})

    def log(self, role, content, class_name=None):
        if class_name is None:
            class_name = self.name
        cur_time = datetime.now().timestamp()
        if not isinstance(content, str):
            content = json.dumps(content, indent=4, ensure_ascii=False)
        self.logger.log(cur_time, role, content, class_name=class_name)

    def log_messages(self, messages):
        for message in messages:
            self.log(message["role"], message["content"])

    def release(self):
        usage_token_total_map = {"completion_tokens": 0, "prompt_tokens": 0, "total_tokens": 0, 'prompt_cost': 0,
                                 'completion_cost': 0, 'total_cost': 0}
        for usage in self.usages:
            usage_token_total_map["completion_tokens"] += usage.completion_tokens
            usage_token_total_map["prompt_tokens"] += usage.prompt_tokens
            usage_token_total_map["total_tokens"] += usage.total_tokens
            usage_token_total_map["prompt_cost"] += usage.prompt_cost
            usage_token_total_map["completion_cost"] += usage.completion_cost
            usage_token_total_map["total_cost"] += usage.total_cost
        self.log("Agent-Network", f"TOKEN TOTAL: {usage_token_total_map}", self.name)
        total_time = sum([usage_time.usage_time for usage_time in self.time_costs])
        self.log("Agent-Network", f"TIME COST TOTAL: {total_time}", self.name)
        self.logger.log("Agent-Network", f"agent: {self.name} has been released")
        return self.usages, self.time_costs


class BaseAgentGroup(Executable):
    def __init__(self, graph, config, logger):
        super().__init__(config["name"], config["task"], config["description"])
        self.config = config
        self.name = self.config["name"]
        self.logger = logger

        self.max_step = self.config["max_step"]

        self.agents: Dict[str, List[GroupAgent]] = {}
        self.current_agents_name: List[str] = []
        self.agent_communication_prompt = dict()
        self.context = dict()

        self.graph = graph
        self.load_graph(graph)
        self.add_routes(graph)
        self.total_time = 0
        self.usage_token_total_map = {"completion_tokens": 0, "prompt_tokens": 0, "total_tokens": 0, 'total_cost': 0,
                                      'prompt_cost': 0, 'completion_cost': 0}

        self.tools = []

    def load_graph(self, graph):
        for agent_item in self.config["agents"]:
            agent_name, agent_config_path = list(agent_item.items())[0]
            with open(agent_config_path, "r", encoding="utf-8") as f:
                agent_config = yaml.safe_load(f)
            agent = self.import_agent(agent_config)
            graph.add_node(agent_name,
                           AgentNode(agent,
                                     agent_config["params"],
                                     agent_config["results"]))
            self.agents.setdefault(agent_name, [])
            self.agents[agent_name].append(GroupAgent(datetime.now().timestamp(), agent_name))
            self.current_agents_name.append(agent_name)

    def add_routes(self, graph: Graph):
        graph.add_route(self.name, self.config["start_agent"], "system")

        if self.config["routes"]:
            for route in self.config["routes"]:
                graph.add_route(route["source"], route["target"], route["type"])

    def import_agent(self, agent_config):
        if agent_config["load_type"] == "module":
            agent_module = importlib.import_module(agent_config["loadModule"])
            agent_class = getattr(agent_module, agent_config["loadClass"])
            agent_instance = agent_class(agent_config, self.logger)
        else:
            raise Exception("Agent load type must be module!")
        return agent_instance

    def execute(self, message, **kwargs):
        # todo start_agent move into route
        return {
            "message": message,
            "next_agent": self.config["start_agent"]
        }

    def add_agent(self, name):
        assert name not in list(self.current_agents_name), f"agent {name} already exist in group {self.name}"
        self.agents.setdefault(name, [])
        self.agents[name].append(GroupAgent(datetime.now().timestamp(), name))

    def remove_agent(self, name):
        assert name in list(self.current_agents_name), f"agent {name} not exist in group {self.name}"
        group_agent_list = self.agents[name]
        self.current_agents_name.remove(name)
        group_agent_list[len(group_agent_list) - 1].end_timestamp = datetime.now().timestamp()
        self.logger.log("Agent-Network", f"agent: {name} has been removed from group: {self.name}", self.name)

    def release(self):
        # for agent in self.agents:
        #     agent_token_usages, agent_time_costs = self.graph.get_node(agent).release()
        #     for group_agent in self.agents[agent]:
        #         if group_agent.end_timestamp == group_agent.begin_timestamp:
        #             group_agent.end_timestamp = datetime.now()
        #         group_agent_total_usage, group_agent_total_time = self._usage_calculate(agent_token_usages, agent_time_costs, group_agent.begin_timestamp, group_agent.end_timestamp)
        #         self.usage_token_total_map["completion_tokens"] += group_agent_total_usage["completion_tokens"]
        #         self.usage_token_total_map["prompt_tokens"] += group_agent_total_usage["prompt_tokens"]
        #         self.usage_token_total_map["total_tokens"] += group_agent_total_usage["total_tokens"]
        #         self.total_time += group_agent_total_time
        # self.logger.log("Agent-Network", f"TOKEN TOTAL: completion_tokens: {self.usage_token_total_map['completion_tokens']}, 'prompt_tokens': {self.usage_token_total_map['prompt_tokens']}, 'total_tokens': {self.usage_token_total_map['total_tokens']}", self.name)
        # self.logger.log("Agent-Network", f"TIME COST TOTAL: {self.total_time}", self.name)
        # self.logger.log("Agent-Network", f"group: {self.name} has been released")
        return self.usage_token_total_map, self.total_time
