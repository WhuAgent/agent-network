import json
from agent_network.message.utils import chat_llm
from datetime import datetime


class BaseAgent:

    def __init__(self, logger, demand):
        self.demand = demand
        self.logger = logger
        self.plan = None
        self.history_action = []
        self.error = None
        self.is_append_history = False
        self.append_history_num = 0
        self.cost_history = []
        self.usages = []

    def initial_messages(self, current_demand):
        messages = []
        return messages

    def initial_prompts(self, current_demand):
        messages = []
        if self.is_append_history and self.append_history_num > 0:
            for i in range(self.append_history_num):
                messages.append({"role": "system", "content": f"第{i + 1}条历史记录:\n"})
                history_action = self.history_action[len(self.history_action) - self.append_history_num + i]
                messages.append({"role": history_action["role"], "content": history_action['content']})
        for message in self.initial_messages(current_demand):
            messages.append(message)
        return messages

    def design(self, messages):
        response, usage = chat_llm(messages)
        self.usages.append(usage)
        self.log(response.role)
        self.log(response.content)
        messages.append({"role": response.role, "content": response.content})
        result, sub_demand_list = self.execute(response.content)
        self.history_action.append({"role": response.role, "content": str(response.content)})
        return response.content, result, sub_demand_list

    def agent_base(self, current_demand=None):
        begin_t = datetime.now()
        result = self.agent(current_demand)
        end_t = datetime.now()
        self.cost_history.append(f"需求: {self.demand if not current_demand else current_demand + '父需求:' + self.demand}, 花费时间: {str(end_t - begin_t)}")
        if not current_demand:
            self.log(self.cost_history)
            self.log(f"总花费时间: {end_t - begin_t}")
            self.log([f"'completion_tokens': {usage.completion_tokens}, 'prompt_tokens': {usage.prompt_tokens}, 'total_tokens': {usage.total_tokens}" for usage in self.usages])
            usage_total_map = {"completion_tokens": 0, "prompt_tokens": 0, "total_tokens": 0}
            for usage in self.usages:
                usage_total_map["completion_tokens"] += usage.completion_tokens
                usage_total_map["prompt_tokens"] += usage.prompt_tokens
                usage_total_map["total_tokens"] += usage.total_tokens
            self.log(f"需求: {self.demand}, 花费token: {usage_total_map}")
        return result

    def agent(self, current_demand=None):
        if not current_demand:
            self.log(f"demand: {self.demand}")
            messages = self.initial_prompts(self.demand)
        else:
            self.log(f"parent demand: {self.demand}, current demand: {current_demand}")
            messages = self.initial_prompts(current_demand)
        self.log_messages(messages)
        content, result, sub_demand_list = self.design(messages)
        if sub_demand_list and len(sub_demand_list) > 0:
            for sub_demand in sub_demand_list:
                result = self.agent(sub_demand)
        return result

    def execute(self, response_content):
        print(f'response_content: {response_content}')
        return None, []

    def append_history(self, number):
        self.is_append_history = True
        self.append_history_num = number

    def log(self, content):
        if not isinstance(content, str):
            content = json.dumps(content, indent=4, ensure_ascii=False)
        print(content)
        self.logger.log(content)

    def log_messages(self, messages):
        for message in messages:
            self.log(message["role"])
            self.log(message["content"])
