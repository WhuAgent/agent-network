import importlib
import json

from agent_network.network.graph import Graph
from agent_network.network.route import Route
from agent_network.network.nodes.graph_node import AgentNode
from datetime import datetime
import yaml
from agent_network.network.executable import Executable
import agent_network.pipeline.context as ctx
from abc import abstractmethod

from time import sleep


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
        self.prompts = self.config["prompts"]
        self.tools = self.config["tools"]
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
    def __init__(self, graph, config, logger):
        super().__init__(config["name"], config["task"], config["description"])
        self.config = config
        self.name = self.config["name"]
        self.logger = logger

        self.max_step = self.config["max_step"]

        self.agents = []
        self.agent_communication_prompt = dict()
        self.context = dict()

        self.load_graph(graph)
        self.add_routes(graph)

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

    def load_routes(self, graph: Graph):
        graph.get_node(self.name).add_route(self.config["start_agent"], "system")
                
        # graph.add_edge(self.name, self.config["start_agent"])
        # self.routes["start"] = Route(self.graph, "start")

        # for agent in self.agents.keys():
        #     self.routes[agent] = Route(self.graph, agent)
        
        agent_communicate_with = dict()

        # self.routes["start"].add_contact(self.config["start_agent"], "system")
        if self.config["routes"]:
            for route in self.config["routes"]:
                # self.routes[route["source"]].add_contact(route["target"], route["type"])
                if route["source"] not in agent_communicate_with:
                    agent_communicate_with[route["source"]] = [route["target"]]
                else:
                    agent_communicate_with[route["source"]].append(route["target"])

            for agent in self.agents.keys():
                prompt = "你还擅长沟通，将与以下智能体合作进行任务：\n"
                for target in agent_communicate_with[agent]:
                    prompt = f'{prompt}{graph.get_node(target).name}: {graph.get_node(target).description}\n'
                # if agent == self.config["end_agent"]:
                #     prompt = f"{prompt}当任务被完成时，你需要将 next_task 设置为 COMPLETE"
                # self.agent_communication_prompt[agent] = prompt
                graph.get_node(agent).add_message("system", prompt)
    
    def execute(self, message, **kwargs):
        return {
            "message": message,
            "next_agent": self.config["start_agent"]
        }
        # cur_agent = "start"
        # nxt_agent = self.config["start_agent"]
        # results = dict()

        # step = 0
        # while step <= self.max_step and demand != "COMPLETE":
        #     results = self.routes[cur_agent].execute(nxt_agent, demand)
        #     cur_agent = nxt_agent
        #     nxt_agent = results.get("next_agent")
        #     demand = results.get("next_task")
        #     step += 1
        
        # return results

