import importlib
import json
from agent_network.utils.llm.openai import chat_llm
from datetime import datetime
import yaml
from agent_network.network.executable import Executable
from abc import abstractmethod
import agent_network.pipeline.context as ctx
from agent_network.entity.usage import UsageToken, UsageTime
from agent_network.entity.group_agent import GroupAgent
from typing import List, Dict

from agent_network.utils.llm.message import SystemMessage, UserMessage, AssistantMessage


class BaseAgent(Executable):

    def __init__(self, graph, config, logger):
        super().__init__(config["name"], config["task"], config["description"])
        self.config = config
        self.graph = graph
        self.task = self.config["task"]
        self.title = self.config["name"]
        self.description = self.config["description"]
        self.class_name = self.config["ref_id"]
        self.role = self.config["role"]
        self.description = self.config["description"]

        self.params = self.config.get("params")
        self.results = self.config.get("results")

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

        self.system_message = self.initial_system_message()

    def initial_system_message(self):
        for message in self.config.get("prompts", []):
            if message["type"] == "inline" and message["role"] == "system":
                self.log("system", message["content"])
                return SystemMessage(message["content"])
            
    def get_system_message(self):
        return self.system_message

    def append_message(self, role, content, messages):
        if role == "system":
            messages.append(SystemMessage(content))
        elif role == "user":
            messages.append(UserMessage(content))
        elif role == "assistant":
            messages.append(AssistantMessage(content))
        else:
            raise Exception("unknown message type")
    
    def add_message(self, role, content, messages=None):
        if messages is None:
            messages = []
        if not (len(messages) > 0 and isinstance(messages[0], SystemMessage)) and self.system_message:
            messages.insert(0, self.system_message)
            self.log("system", self.system_message.content, self.__class__.__name__)
        self.append_message(role, content, messages)
        self.log(role, content)
        if self.append_history_num > 0:
            for i in range(min(self.append_history_num, len(self.history_action))):
                self.append_message("system", f"{i + 1}th historical records:\n", messages)
                history_action = self.history_action[len(self.history_action) - self.append_history_num + i]
                self.append_message(history_action["role"], history_action["content"], messages)
        return messages

    @abstractmethod
    def forward(self, messages, **kwargs):
        results = dict()
        return messages, results

    def execute(self, messages, **kwargs):
        begin_t = datetime.now().timestamp()
        messages, results = self.forward(messages, **kwargs)
        end_t = datetime.now().timestamp()
        self.log("network", f"AGENT {self.name} time cost: {end_t - begin_t}", self.name)
        time_cost = end_t - begin_t
        self.time_costs.append(UsageTime(begin_t, time_cost))
        return messages, results

    def chat_llm(self, messages):
        # todo 该时间不精准，应该取execute的开始时间
        time_chat_begin = datetime.now().timestamp()
        assistant_message = chat_llm(messages, self.model)
        messages.append(assistant_message)
        self.log(assistant_message.role, assistant_message.content)
        usage_token_map = {'completion_tokens': assistant_message.completion_token_num, 'prompt_tokens': assistant_message.prompt_token_num,
                           'total_tokens': assistant_message.token_num, 'total_cost': assistant_message.token_cost,
                           'completion_cost': assistant_message.completion_token_cost, 'prompt_cost': assistant_message.prompt_token_cost}
        self.usages.append(UsageToken(time_chat_begin, usage_token_map))
        
        ctx.register_llm_action(messages)
        self.log("network", f"STEP TOKEN NUM: {assistant_message.token_num} COST: {assistant_message.token_cost}")
        if len(self.history_action) > 0 and len(self.history_action) >= self.keep_history_num:
            self.history_action.pop(0)
        self.history_action.append({"role": assistant_message.role, "content": assistant_message.content})
        return assistant_message

    def log(self, role, content, instance=None):
        if instance is None:
            instance = self.name
        if not isinstance(content, str):
            content = json.dumps(content, indent=4, ensure_ascii=False)
        self.logger.log(role, content, instance=instance)

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
        self.log("Agent-Network-Agent", f"AGENT TOKEN TOTAL: {usage_token_total_map}", self.name)
        total_time = sum([usage_time.usage_time for usage_time in self.time_costs])
        self.log("Agent-Network-Agent", f"AGENT TIME COST TOTAL: {total_time}", self.name)
        self.log("Agent-Network-Agent", f"AGENT: {self.name} has been released")
        return self.usages, self.time_costs


class BaseAgentGroup(Executable):
    def __init__(self, graph, route, config, logger):
        super().__init__(config["name"], config["task"], config["description"])
        self.config = config
        self.name = self.config["name"]
        self.logger = logger
        self.graph = graph
        self.route = route
        self.class_name = self.config["ref_id"] if "ref_id" in self.config else None

        self.max_step = self.config["max_step"]

        self.params = self.config.get("params")
        self.results = self.config.get("results")

        self.routes = []
        for route in self.config["routes"]:
            self.routes.append({
                "group": self.name,
                "source": route["source"],
                "target": route["target"],
                "type": route["type"],
                "rule": route["rule"] if "rule" in route else None
            })

        self.agents: Dict[str, List[GroupAgent]] = {}
        self.start_agent = self.config.get("start_agent")

        self.current_agents_name: List[str] = []
        self.agent_communication_prompt = dict()
        self.context = dict()

        self.tools = []

    def load_agents(self) -> list[BaseAgent]:
        agents = []
        for agent_item in self.config["agents"]:
            agent_name, agent_config_path = list(agent_item.items())[0]
            exist_agent_node = self.graph.get_node(agent_name)
            if exist_agent_node is not None:
                agent = exist_agent_node.executable
            else:
                with open(agent_config_path, "r", encoding="utf-8") as f:
                    agent_config = yaml.safe_load(f)
                agent = self.import_agent(agent_config)
            agents.append(agent)
            self.agents.setdefault(agent_name, [])
            self.agents[agent_name].append(GroupAgent(datetime.now().timestamp(), agent_name))
            self.current_agents_name.append(agent_name)
        return agents

    def import_agent(self, agent_config):
        if agent_config["load_type"] == "module":
            agent_module = importlib.import_module(agent_config["loadModule"])
            agent_class = getattr(agent_module, agent_config["loadClass"])
            agent_instance = agent_class(self.graph, agent_config, self.logger)
        else:
            raise Exception("Agent load type must be module!")
        return agent_instance

    def execute(self, message, **kwargs):
        # todo start_agent move into route
        results = {
            "message": message,
            "next_agent": self.config["start_agent"]
        }
        return message, results

    def add_agent(self, name):
        assert name not in list(self.current_agents_name), f"agent {name} already exist in group {self.name}"
        self.agents.setdefault(name, [])
        self.agents[name].append(GroupAgent(datetime.now().timestamp(), name))

    def remove_agent(self, name):
        assert name in list(self.current_agents_name), f"agent {name} not exist in group {self.name}"
        group_agent_list = self.agents[name]
        self.current_agents_name.remove(name)
        group_agent_list[len(group_agent_list) - 1].end_timestamp = datetime.now().timestamp()
        self.logger.log("Agent-Network-Group", f"agent: {name} has been removed from group: {self.name}", self.name)

    def remove_agent_if_exist(self, name):
        if name in list(self.current_agents_name):
            self.remove_agent(name)

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
        self.logger.log("Agent-Network-Group", f"GROUP: {self.name} has been released")
        return self.usage_token_total_map, self.total_time
