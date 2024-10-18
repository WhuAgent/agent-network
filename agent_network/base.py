import importlib
import json
import pika
from agent_network.network.route import Route
from agent_network.network.nodes.node import Node
from agent_network.message.utils import chat_llm
from datetime import datetime
import yaml
from agent_network.network.executable import Executable
from abc import abstractmethod


class BaseAgent(Executable):

    def __init__(self, logger, name, title, task, role, description, history_number, prompts, tools,
                 runtime_revision_number, **kwargs):
        super().__init__(name, task)
        self.task = task
        self.title = title
        self.name = name
        self.role = role
        self.description = description
        self.prompts = prompts
        self.tools = tools
        self.logger = logger
        self.if_error = False
        self.error = None
        self.history_action = []
        self.append_history_num = history_number
        self.runtime_revision_number = runtime_revision_number
        self.cost_history = []
        self.usages = []
        self.context = {**kwargs}
        self.start_communication()

    def start_communication(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.channel = self.connection.channel()

        exchange_name = f"{self.name}Exchange"
        queue_name = f"{self.name}"

        self.channel.exchange_declare(exchange=exchange_name, exchange_type='direct')
        self.channel.queue_declare(queue=queue_name, durable=True)
        self.channel.queue_bind(exchange=exchange_name, queue=queue_name, routing_key=queue_name)
        self.channel.basic_consume(queue=queue_name, on_message_callback=self.on_message, auto_ack=True)
        self.channel.start_consuming()

    def initial_messages(self, current_task, **kwargs):
        messages = []
        for prompt in self.prompts:
            prompt_messages = []
            if prompt.type == "file":
                for content in prompt.contents:
                    with open(content, "r", encoding="UTF-8") as f:
                        prompt = yaml.safe_load(f)
                        prompt["task_prompt"] = prompt["task_prompt"].replace("{task}", f"{current_task}")
                        prompt_messages.extend([
                            {"role": "system", "content": prompt["system_prompt"]},
                            {"role": "user", "content": prompt["task_prompt"]}
                        ])
            elif prompt.type == "inline":
                inline_messages = []
                for content in prompt.contents:
                    prompt_content = json.load(content)
                    inline_messages.append({"role": prompt_content["role"],
                                            "content": prompt_content["content"].replace("{task}", current_task)})
                prompt_messages.extend(inline_messages)
            messages.extend(prompt_messages)
        return messages

    def initial_prompts(self, current_task, **kwargs):
        messages = []
        if self.append_history_num > 0:
            for i in range(min(self.append_history_num, len(self.history_action))):
                messages.append({"role": "system", "content": f"第{i + 1}条历史记录:\n"})
                history_action = self.history_action[len(self.history_action) - self.append_history_num + i]
                messages.append({"role": history_action["role"], "content": history_action['content']})
        messages.extend(self.initial_messages(current_task, **kwargs))
        return messages

    def before_agent(self, content):
        pass

    def after_agent(self, success, result, message_to, context):
        pass

    def design(self, messages, **kwargs):
        response, usage = chat_llm(messages)
        self.usages.append(usage)
        self.log(response.role, response.content)
        messages.append({"role": response.role, "content": response.content})
        next_task, results, sub_task_list = self.execute(response.content, **kwargs)
        self.history_action.append({"role": response.role, "content": str(response.content)})
        return response.content, next_task, results, sub_task_list

    def agent_base(self, current_task=None, **kwargs):
        begin_t = datetime.now()
        self.pre_agent(**kwargs)
        next_task, results = self.agent(self.runtime_revision_number, current_task, **kwargs)
        self.post_agent(**kwargs)
        end_t = datetime.now()
        self.cost_history.append(
            f"需求: {self.task if not current_task else current_task + '父需求:' + self.task}, 花费时间: {str(end_t - begin_t)}")
        if not current_task:
            self.log(self.name, self.cost_history)
            self.log(self.name, f"总花费时间: {end_t - begin_t}")
            self.log(self.name, [
                f"'completion_tokens': {usage.completion_tokens}, 'prompt_tokens': {usage.prompt_tokens}, 'total_tokens': {usage.total_tokens}"
                for usage in self.usages])
            usage_total_map = {"completion_tokens": 0, "prompt_tokens": 0, "total_tokens": 0}
            for usage in self.usages:
                usage_total_map["completion_tokens"] += usage.completion_tokens
                usage_total_map["prompt_tokens"] += usage.prompt_tokens
                usage_total_map["total_tokens"] += usage.total_tokens
            self.log(self.name, f"需求: {self.task}, 花费token: {usage_total_map}")
        return next_task, results
        # begin_t = datetime.now()
        # content = self.before_agent(content)
        # self.log(message_from, content, self.class_name)
        # self.messages.append({"role": "user", "content": content})
        # success, result, message_to, context = self.agent(self.runtime_revision_number, content)
        # self.after_agent(success, result, message_to, context)
        # end_t = datetime.now()
        # return result

    def on_message(self, ch, method, properties, body):
        pass

    def post_agent(self, **kwargs):
        pass

    def pre_agent(self, **kwargs):
        pass

    def agent(self, runtime_revision_number, current_task=None, **kwargs):
        if not current_task:
            self.log(self.name, f"task: {self.task}")
            messages = self.initial_prompts(self.task, **kwargs)
        else:
            self.log(self.name, f"parent task: {self.task}, current task: {current_task}")
            messages = self.initial_prompts(current_task, **kwargs)
        self.log_messages(messages)
        content, next_task, results, sub_task_list = self.design(messages, **kwargs)
        if sub_task_list and len(sub_task_list) > 0:
            if runtime_revision_number > 0:
                for sub_task in sub_task_list:
                    next_task, sub_results = self.agent(runtime_revision_number - 1, sub_task)
                    results = {**results, **sub_results}
            else:
                raise Exception("reach max runtime revision number, task failed")
        return next_task, results

    @abstractmethod
    def execute(self, response_content, **kwargs):
        print(f'response_content: {response_content}')
        return None, None, []

    def log(self, role, content, class_name=None):
        if class_name is None:
            class_name = self.name
        cur_time = datetime.now()
        if not isinstance(content, str):
            content = json.dumps(content, indent=4, ensure_ascii=False)
        print(content)
        self.logger.log(cur_time, role, content, class_name=class_name)

    def log_messages(self, messages):
        for message in messages:
            self.log(message["role"], message["content"])


class BaseAgentGroup(Executable):
    def __init__(self, configs, graph, logger):
        super().__init__(configs["name"], configs["task"])
        self.config = configs
        self.name = self.config["name"]
        self.logger = logger
        self.agents = []
        self.routes = {}
        for route_config in self.config["routes"]:
            if route_config["source"] not in self.routes:
                self.routes[route_config["source"]] = []
            route = Route(route_config["source"], route_config["target"], route_config["type"])
            self.routes[route_config["source"]].append(route)

        self.tools = []
        self.load(graph)
        self.graph = graph

    def load(self, graph):
        for agent_item in self.config["agents"]:
            agent_name, agent_config_path = list(agent_item.items())[0]
            with open(agent_config_path, "r", encoding="utf-8") as f:
                agent_config = yaml.safe_load(f)
                agent = self.import_agent(agent_config)
                graph.add_node(agent_name, Node(agent, agent_config["params"], agent_config["results"]))

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
                agent_instance = agent_class(self.logger, agent_config["name"], agent_config["title"],
                                             agent_config["task"],
                                             agent_config["role"],
                                             agent_config["description"], agent_config["history_number"],
                                             agent_config["prompts"],
                                             agent_config["tools"], agent_config["runtime_revision_number"],
                                             )
        else:
            raise Exception("Agent load type must be module!")
        return agent_instance

    def execute(self, task, **kwargs):
        for start_route in self.routes["start"]:
            start_route.execute(self.graph, task)
