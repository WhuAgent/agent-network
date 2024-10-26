import importlib
import json

from agent_network.network.graph import Graph
from agent_network.network.route import Route, RabbitMQRoute
from agent_network.network.nodes.node import Node
from agent_network.network.nodes.graph_node import AgentNode
from datetime import datetime
import yaml
from agent_network.network.executable import Executable
import agent_network.pipeline.context as ctx
from abc import abstractmethod

from time import sleep


class BaseAgent(Executable):

    def __init__(self, config, logger):
        super().__init__(config["name"], config["task"])
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
        self.prompts = self.config["prompts"]
        self.tools = self.config["tools"]
        self.communication_config = self.config["communication"]
        self.logger = logger
        self.if_error = False
        self.error = None
        self.history_action = []
        self.append_history_num = 0
        self.runtime_revision_number = 0
        self.cost_history = []
        self.usages = []

        self.messages = []
        self.initial_messages()

    def add_message(self, role, content):
        self.messages.append({
            "role": role,
            "content": content
        })
        self.log(role, content, self.__class__.__name__)

    @abstractmethod
    def initial_messages(self):
        raise NotImplementedError

    @abstractmethod
    def forward(self, message, **kwargs):
        results = dict()
        return results

    def execute(self, current_task, **kwargs):
        begin_t = datetime.now()
        results = self.forward(current_task, **kwargs)
        end_t = datetime.now()
        # self.cost_history.append(
        #     f"需求: {self.task if not current_task else current_task + '父需求:' + self.task}, 花费时间: {str(end_t - begin_t)}")
        # if not current_task:
        #     self.log(self.name, self.cost_history)
        #     self.log(self.name, f"总花费时间: {end_t - begin_t}")
        #     self.log(self.name, [
        #         f"'completion_tokens': {usage.completion_tokens}, 'prompt_tokens': {usage.prompt_tokens}, 'total_tokens': {usage.total_tokens}"
        #         for usage in self.usages])
        #     usage_total_map = {"completion_tokens": 0, "prompt_tokens": 0, "total_tokens": 0}
        #     for usage in self.usages:
        #         usage_total_map["completion_tokens"] += usage.completion_tokens
        #         usage_total_map["prompt_tokens"] += usage.prompt_tokens
        #         usage_total_map["total_tokens"] += usage.total_tokens
        #     self.log(self.name, f"需求: {self.task}, 花费token: {usage_total_map}")
        return results

    def log(self, role, content, class_name=None):
        if class_name is None:
            class_name = self.name
        cur_time = datetime.now()
        if not isinstance(content, str):
            content = json.dumps(content, indent=4, ensure_ascii=False)
        # print(content)
        self.logger.log(cur_time, role, content, class_name=class_name)

    def log_messages(self, messages):
        for message in messages:
            self.log(message["role"], message["content"])


class BaseAgentGroup(Executable):
    def __init__(self, config, logger):
        super().__init__(config["name"], config["task"])
        self.config = config
        self.name = self.config["name"]
        self.logger = logger

        self.block_flag = self.config["block_flag"]

        self.agents = dict()
        self.agent_communication_prompt = dict()
        self.context = dict()

        self.graph = Graph(self.name, None, None, None)
        self.load_graph()

        self.route_threads = []
        self.routes = dict()
        self.load_routes()

        self.tools = []

    def load_graph(self):
        for agent_item in self.config["agents"]:
            agent_name, agent_config_path = list(agent_item.items())[0]
            with open(agent_config_path, "r", encoding="utf-8") as f:
                agent_config = yaml.safe_load(f)
                agent = self.import_agent(agent_config)
                self.agents[agent_name] = agent
                self.graph.add_node(agent_name,
                                    AgentNode(agent,
                                              agent_config["name"],
                                              agent_config["task"],
                                              agent_config["params"],
                                              agent_config["results"]))

    def import_agent(self, agent_config):
        if agent_config["load_type"] == "module":
            agent_module = importlib.import_module(agent_config["loadModule"])
            agent_class = getattr(agent_module, agent_config["loadClass"])
            if agent_config["init_extra_params"]:
                agent_instance = agent_class(self.logger, agent_config["name"], agent_config["title"],
                                             agent_config["task"],
                                             agent_config["role"],
                                             agent_config["description"], agent_config["history_number"],
                                             agent_config["prompts"],
                                             agent_config["tools"], agent_config["runtime_revision_number"],
                                             **agent_config["init_extra_params"]
                                             )
            else:
                agent_instance = agent_class(agent_config, self.logger)
        else:
            raise Exception("Agent load type must be module!")
        return agent_instance

    def load_routes(self):
        self.routes["start"] = Route(self.graph, "start")

        for agent in self.agents.keys():
            self.routes[agent] = Route(self.graph, agent)
        
        agent_communicate_with = dict()

        self.routes["start"].add_contact(self.config["start_agent"], "system")
        if self.config["routes"]:
            for route in self.config["routes"]:
                self.routes[route["source"]].add_contact(route["target"], route["type"])
                if route["source"] not in agent_communicate_with:
                    agent_communicate_with[route["source"]] = [route["target"]]
                else:
                    agent_communicate_with[route["source"]].append(route["target"])

            for agent in self.agents.keys():
                prompt = "你还擅长沟通，将与以下智能体合作进行任务：\n"
                for target in agent_communicate_with[agent]:
                    prompt = f'{prompt}{self.agents[target].name}: {self.agents[target].description}\n'
                if agent == self.config["end_agent"]:
                    prompt = f"{prompt}当任务被完成时，你需要将 next_task 设置为 COMPLETE"
                # self.agent_communication_prompt[agent] = prompt
                self.agents[agent].add_message("system", prompt)
    
    def execute(self, demand, **kwargs):
        cur_execution_agent = "start"
        nxt_execution_agent = self.config["start_agent"]

        step = 0
        while step <= 100:
            if demand == "COMPLETE":
                break
            results = self.routes[cur_execution_agent].execute(nxt_execution_agent, demand)
            cur_execution_agent = nxt_execution_agent
            nxt_execution_agent = results.get("next_agent")
            demand = results.get("next_task")

