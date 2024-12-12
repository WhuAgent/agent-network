import importlib
import json
from agent_network.message.utils import chat_llm
from agent_network.network.graph import Graph
from agent_network.network.nodes.graph_node import AgentNode
from datetime import datetime
import yaml
from agent_network.network.executable import Executable
from abc import abstractmethod
import agent_network.pipeline.context as ctx


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
        self.usages = []
        self.time_costs = []

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
        begin_t = datetime.now()
        results = self.forward(current_task, **kwargs)
        end_t = datetime.now()
        self.log("Agent-Network", f"{self.name} time cost: {end_t - begin_t}", self.name)
        time_cost = end_t - begin_t
        self.time_costs.append(time_cost)
        ctx.register_time(self.name, time_cost)
        return results

    def chat_llm(self, messages):
        response, usage = chat_llm(messages)
        self.usages.append(usage)
        ctx.register_usage({'completion_tokens': usage.completion_tokens, 'prompt_tokens': usage.prompt_tokens, 'total_tokens': usage.total_tokens})
        self.log("Agent-Network", f"'completion_tokens': {usage.completion_tokens}, 'prompt_tokens': {usage.prompt_tokens}, 'total_tokens': {usage.total_tokens}", self.name)
        if len(self.history_action) >= self.keep_history_num:
            self.history_action.pop(0)
        self.history_action.append({"role": response.role, "content": str(response.content)})

    def log(self, role, content, class_name=None):
        if class_name is None:
            class_name = self.name
        cur_time = datetime.now()
        if not isinstance(content, str):
            content = json.dumps(content, indent=4, ensure_ascii=False)
        self.logger.log(cur_time, role, content, class_name=class_name)

    def log_messages(self, messages):
        for message in messages:
            self.log(message["role"], message["content"])

    def release(self):
        usage_token_total_map = {"completion_tokens": 0, "prompt_tokens": 0, "total_tokens": 0}
        for usage in self.usages:
            usage_token_total_map["completion_tokens"] += usage.completion_tokens
            usage_token_total_map["prompt_tokens"] += usage.prompt_tokens
            usage_token_total_map["total_tokens"] += usage.total_tokens
        # self.log(self.name, [
        #     f"'completion_tokens': {usage.completion_tokens}, 'prompt_tokens': {usage.prompt_tokens}, 'total_tokens': {usage.total_tokens}"
        #     for usage in self.usages])
        self.log("Agent-Network", f"TOKEN TOTAL: completion_tokens: {usage_token_total_map['completion_tokens']}, 'prompt_tokens': {usage_token_total_map['prompt_tokens']}, 'total_tokens': {usage_token_total_map['total_tokens']}", self.name)
        total_time = sum(self.time_costs)
        self.log("Agent-Network", f"TIME COST TOTAL: {total_time}", self.name)
        self.logger.log("Agent-Network", f"agent: {self.name} has been released")
        return usage_token_total_map, total_time


class BaseAgentGroup(Executable):
    def __init__(self, graph, config, logger):
        super().__init__(config["name"], config["task"], config["description"])
        self.config = config
        self.name = self.config["name"]
        self.logger = logger

        self.max_step = self.config["max_step"]

        self.agents = []
        self.agent_communication_prompt = dict()
        self.context = dict()

        self.graph = graph
        self.load_graph(graph)
        self.add_routes(graph)
        self.total_time = 0
        self.usage_token_total_map = {"completion_tokens": 0, "prompt_tokens": 0, "total_tokens": 0}

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
            self.agents.append(agent_name)

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
        assert name not in self.agents, f"agent {name} already exist in group {self.name}"
        self.agents.append(name)

    def remove_agent(self, name):
        assert name in self.agents, f"agent {name} not exist in group {self.name}"
        self.agents.remove(name)
        usage_token_total_map, total_time = self.graph.get_node(name).release()
        self.usage_token_total_map["completion_tokens"] += usage_token_total_map["completion_tokens"]
        self.usage_token_total_map["prompt_tokens"] += usage_token_total_map["prompt_tokens"]
        self.usage_token_total_map["total_tokens"] += usage_token_total_map["total_tokens"]
        self.total_time += total_time
        self.logger.log("Agent-Network", f"agent: {name} has been removed from group: {self.name}", self.name)

    def release(self):
        for agent in self.agents:
            usage_token_total_map, total_time = self.graph.get_node(agent).release()
            self.usage_token_total_map["completion_tokens"] += usage_token_total_map["completion_tokens"]
            self.usage_token_total_map["prompt_tokens"] += usage_token_total_map["prompt_tokens"]
            self.usage_token_total_map["total_tokens"] += usage_token_total_map["total_tokens"]
            self.total_time += total_time
        self.logger.log("Agent-Network", f"TOKEN TOTAL: completion_tokens: {self.usage_token_total_map['completion_tokens']}, 'prompt_tokens': {self.usage_token_total_map['prompt_tokens']}, 'total_tokens': {self.usage_token_total_map['total_tokens']}", self.name)
        self.logger.log("Agent-Network", f"TIME COST TOTAL: {self.total_time}", self.name)
        self.logger.log("Agent-Network", f"group: {self.name} has been released")
        return self.usage_token_total_map, self.total_time
