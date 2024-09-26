import importlib
import threading
import json
import pika


import click
from tenacity import sleep

from agent_network.message.utils import chat_llm
from datetime import datetime
import yaml
from agent_network.pipeline.node import Executable
from tbot.util import send_message


class BaseAgent:

    def __init__(self, config_path, logger, context):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        self.logger = logger

        self.task = self.config["task"]
        self.title = self.config["name"]
        self.class_name = self.config["ref_id"]
        self.role = self.config["role"]
        self.description = self.config["description"]
        self.prompts = self.config["prompts"]
        self.messages = self.initial_messages()
        self.tools = self.config["tools"]
        self.logger = logger
        self.if_error = False
        self.error = None
        self.history_action = []
        self.append_history_num = 0
        self.runtime_revision_number = 0
        self.cost_history = []
        self.usages = []
        self.context = context

        self.start_communication()

    def start_communication(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.channel = self.connection.channel()

        exchange_name = f"{self.config['name']}Exchange"
        queue_name = f"{self.config['name']}"

        self.channel.exchange_declare(exchange=exchange_name, exchange_type='direct')
        self.channel.queue_declare(queue=queue_name, durable=True)
        self.channel.queue_bind(exchange=exchange_name, queue=queue_name, routing_key=queue_name)
        self.channel.basic_consume(queue=queue_name, on_message_callback=self.on_message, auto_ack=True)
        self.channel.start_consuming()

    def initial_messages(self):
        messages = []
        for prompt in self.config["prompts"]:
            if prompt["type"] == "inline" and prompt["role"] == "system":
                messages.append({
                    "role": prompt["role"],
                    "content": prompt["content"]
                })
                self.log(prompt["role"], prompt["content"], self.class_name)
            # else:
            #     raise Exception("Prompt type must be inline!")
        return messages

    def initial_prompts(self, current_task):
        messages = []
        if self.append_history_num > 0:
            for i in range(self.append_history_num):
                messages.append({"role": "system", "content": f"第{i + 1}条历史记录:\n"})
                history_action = self.history_action[len(self.history_action) - self.append_history_num + i]
                messages.append({"role": history_action["role"], "content": history_action['content']})
        messages.extend(self.initial_messages(current_task))
        return messages

    def before_agent(self, content):
        pass

    def after_agent(self, success, result, message_to, context):
        pass

    def agent(self, runtime_revision_number, current_task=None):
        context = ""
        if self.config["need_chat"]:
            # if not current_task:
            #     # self.log(f"task: {self.task}")
            #     messages = self.initial_prompts(self.task)
            # else:
            #     # self.log(self.role, f"parent task: {self.task}, current task: {current_task}")
            #     messages = self.initial_prompts(current_task)
            # self.log_messages(messages)

            response, usage = chat_llm(self.messages)
            self.usages.append(usage)
            self.log(response.role, response.content)
            self.messages.append({"role": response.role, "content": response.content})
            self.history_action.append({"role": response.role, "content": str(response.content)})
            context = response.content

        # if sub_task_list and len(sub_task_list) > 0 and runtime_revision_number > 0:
        #     for sub_task in sub_task_list:
        #         result = self.agent(runtime_revision_number - 1, sub_task)
        return self.execute(context)

    def execute(self, response_content):
        result = ""
        new_context = ""
        message_to = ""
        return result, message_to, new_context

    def forward(self, message_from, content):
        begin_t = datetime.now()
        content = self.before_agent(content)
        self.log(message_from, content, self.class_name)
        self.messages.append({"role": "user", "content": content})
        success, result, message_to, context = self.agent(self.runtime_revision_number, content)
        self.after_agent(success, result, message_to, context)
        end_t = datetime.now()

        # self.cost_history.append(f"需求: {self.task if not current_task else current_task}, "
        #                          f"父需求: {self.task}, "
        #                          f"花费时间: {str(end_t - begin_t)}")
        # if not current_task:
        #     self.log(self.cost_history)
        #     self.log(f"总花费时间: {end_t - begin_t}")
        #     self.log([f"'completion_tokens': {usage.completion_tokens}, "
        #               f"'prompt_tokens': {usage.prompt_tokens}, "
        #               f"'total_tokens': {usage.total_tokens}"
        #               for usage in self.usages])
        #     usage_total_map = {"completion_tokens": 0, "prompt_tokens": 0, "total_tokens": 0}
        #     for usage in self.usages:
        #         usage_total_map["completion_tokens"] += usage.completion_tokens
        #         usage_total_map["prompt_tokens"] += usage.prompt_tokens
        #         usage_total_map["total_tokens"] += usage.total_tokens
        #     self.log(f"需求: {self.task}, 花费token: {usage_total_map}")
        return result

    def on_message(self, ch, method, properties, body):
        pass

    def log(self, role, content, class_name=None):
        if class_name is None:
            class_name = self.class_name
        cur_time = datetime.now()
        if not isinstance(content, str):
            content = json.dumps(content, indent=4, ensure_ascii=False)
        # print(content)
        self.logger.log(cur_time, role, content, class_name=class_name)

    def log_messages(self, messages):
        for message in messages:
            self.log(message["role"], message["content"])

    def register(self, key, value):
        self.context[key] = value

    def insert(self, key, value):
        self.context[key].update(value)

    def retrieve(self, key):
        if key not in self.context:
            raise Exception(f"context do not contain key: {key}")
        return self.context[key]

    def get_prompt(self, role):
        for prompt in self.config["prompts"]:
            if prompt["role"] == role:
                return prompt["content"]


class BaseGroup:
    def __init__(self, config_path, logger, global_context):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        self.logger = logger
        self.global_context = global_context

        self.agents = []
        self.start_agent = self.config["start_agent"]
        self.agent_module_map = dict()
        self.tools = []
        self.next_group = []

        self.load()


    def load(self):
        for agent_item in self.config["agents"]:
            agent_name, agent_config_path = list(agent_item.items())[0]
            self.agent_module_map[agent_name] = threading.Thread(target=self.import_agent,
                                                                 args=(agent_config_path,
                                                                       self.logger,
                                                                       self.global_context))

        for thread in self.agent_module_map.values():
            thread.start()

    @staticmethod
    def import_agent(agent_config_path, logger, global_context):
        with open(agent_config_path, "r", encoding="utf-8") as f:
            agent_config = yaml.safe_load(f)

        if agent_config["load_type"] == "module":
            agent_module = importlib.import_module(agent_config["loadModule"])
            agent_class = getattr(agent_module, agent_config["loadClass"])
            agent = agent_class(agent_config_path, logger, global_context)
        else:
            raise Exception("Agent load type must be module!")

        return agent

    def get_prompt(self, role):
        for prompt in self.config["prompts"]:
            if prompt["role"] == role:
                return prompt["content"]

    def forward(self, *args, **kwargs):
        self.global_context["task"] = kwargs["current_task"]
        # click.echo(click.style("hello", fg="green"))
        # click.echo(click.style(json.dumps(self.global_context, indent=4, ensure_ascii=False), fg="green"))
        start_agent = self.config["start_agent"]
        header = {
            "message_from": "user"
        }
        content = self.get_prompt("start")
        send_message(start_agent, header, content)

        while "complete" not in self.global_context.keys():
            sleep(1)
            # print("tired")
            # print(json.dumps(self.global_context, indent=4, ensure_ascii=False, default=str))

        for thread in self.agent_module_map.keys():
            send_message(thread, {}, "complete")
        self.agent_module_map.clear()

        code = self.generate_code()

        cur_time = datetime.now()
        self.logger.log(cur_time, content=code)

    def generate_code(self):
        codes = []

        for variable in self.global_context["variable_memory"]:
            code = f'Dim {variable.name} = ""'
            codes.append(code)

        codes.append("\n")

        for code in self.global_context["code"]:
            codes.append(code)

        code = "\n".join(codes)
        print(code)
        return code
