import importlib
import threading
import json
import pika


import click
from tenacity import sleep

from agent_network.message.utils import chat_llm
from datetime import datetime
import yaml
from agent_network.pipeline.executable import Executable
from abc import abstractmethod


class BaseAgent(Executable):

    def __init__(self, logger, name, title, task, role, description, history_number, prompts, tools,
                 runtime_revision_number, **kwargs):
        super().__init__(name, task, {}, {})
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

        exchange_name = f"{self.config['name']}Exchange"
        queue_name = f"{self.config['name']}"

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
        self.log(response.role)
        self.log(response.content)
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
            self.log(self.cost_history)
            self.log(f"总花费时间: {end_t - begin_t}")
            self.log([
                f"'completion_tokens': {usage.completion_tokens}, 'prompt_tokens': {usage.prompt_tokens}, 'total_tokens': {usage.total_tokens}"
                for usage in self.usages])
            usage_total_map = {"completion_tokens": 0, "prompt_tokens": 0, "total_tokens": 0}
            for usage in self.usages:
                usage_total_map["completion_tokens"] += usage.completion_tokens
                usage_total_map["prompt_tokens"] += usage.prompt_tokens
                usage_total_map["total_tokens"] += usage.total_tokens
            self.log(f"需求: {self.task}, 花费token: {usage_total_map}")
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
            self.log(f"task: {self.task}")
            messages = self.initial_prompts(self.task, **kwargs)
        else:
            self.log(f"parent task: {self.task}, current task: {current_task}")
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
        # print(content)
        self.logger.log(cur_time, role, content, class_name=class_name)

    def log_messages(self, messages):
        for message in messages:
            self.log(message["role"], message["content"])

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
