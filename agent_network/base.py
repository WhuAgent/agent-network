import json
from agent_network.message.utils import chat_llm
from datetime import datetime
import yaml
from agent_network.pipeline.node import Executable
from abc import abstractmethod


class BaseAgent(Executable):

    def __init__(self, logger, title, task, role, description, history_number, prompts, tools,
                 runtime_revision_number, **kwargs):
        super().__init__(title, task)
        self.task = task
        self.title = title
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

    def initial_messages(self, current_task):
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

    def initial_prompts(self, current_task):
        messages = []
        if self.append_history_num > 0:
            for i in range(self.append_history_num):
                messages.append({"role": "system", "content": f"第{i + 1}条历史记录:\n"})
                history_action = self.history_action[len(self.history_action) - self.append_history_num + i]
                messages.append({"role": history_action["role"], "content": history_action['content']})
        messages.extend(self.initial_messages(current_task))
        return messages

    def design(self, messages):
        response, usage = chat_llm(messages)
        self.usages.append(usage)
        self.log(response.role)
        self.log(response.content)
        messages.append({"role": response.role, "content": response.content})
        result, sub_task_list = self.execute(response.content)
        self.history_action.append({"role": response.role, "content": str(response.content)})
        return response.content, result, sub_task_list

    def agent_base(self, current_task=None):
        begin_t = datetime.now()
        self.pre_agent()
        result = self.agent(self.runtime_revision_number, current_task)
        self.post_agent()
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
        return result

    def post_agent(self):
        pass

    def pre_agent(self):
        pass

    def agent(self, runtime_revision_number, current_task=None):
        if not current_task:
            self.log(f"task: {self.task}")
            messages = self.initial_prompts(self.task)
        else:
            self.log(f"parent task: {self.task}, current task: {current_task}")
            messages = self.initial_prompts(current_task)
        self.log_messages(messages)
        content, result, sub_task_list = self.design(messages)
        if sub_task_list and len(sub_task_list) > 0:
            if runtime_revision_number > 0:
                for sub_task in sub_task_list:
                    result = self.agent(runtime_revision_number - 1, sub_task)
            else:
                raise Exception("reach max runtime revision number, task failed")
        return result

    @abstractmethod
    def execute(self, response_content):
        print(f'response_content: {response_content}')
        return None, []

    def log(self, content):
        if not isinstance(content, str):
            content = json.dumps(content, indent=4, ensure_ascii=False)
        print(content)
        self.logger.log(content)

    def log_messages(self, messages):
        for message in messages:
            self.log(message["role"])
            self.log(message["content"])
