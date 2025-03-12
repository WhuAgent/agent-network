from openai.types.completion_usage import CompletionUsage

model_cost = {
    "gpt-3.5-turbo": {
        "prompt_token": 0.0035,
        "completion_token": 0.0105
    },
    "gpt-3.5-turbo-1106": {
        "prompt_token": 0.007,
        "completion_token": 0.014
    },
    "gpt-3.5-turbo-0125": {
        "prompt_token": 0.0035,
        "completion_token": 0.0105
    },
    "gpt-3.5-turbo-16k": {
        "prompt_token": 0.021,
        "completion_token": 0.028
    },
    "gpt-3.5-turbo-instruct": {
        "prompt_token": 0.0105,
        "completion_token": 0.014
    },
    "o1-mini": {
        "prompt_token": 0.021,
        "completion_token": 0.084
    },
    "o1-preview": {
        "prompt_token": 0.105,
        "completion_token": 0.42
    },
    "gpt-4": {
        "prompt_token": 0.21,
        "completion_token": 0.42
    },
    "gpt-4o": {
        "prompt_token": 0.0175,
        "completion_token": 0.07
    },
    "gpt-4o-2024-05-13": {
        "prompt_token": 0.035,
        "completion_token": 0.105
    },
    "gpt-4o-2024-08-06": {
        "prompt_token": 0.0175,
        "completion_token": 0.07
    },
    "gpt-4o-2024-11-20": {
        "prompt_token": 0.0175,
        "completion_token": 0.07
    },
    "chatgpt-4o-latest": {
        "prompt_token": 0.035,
        "completion_token": 0.105
    },
    "gpt-4o-mini": {
        "prompt_token": 0.00105,
        "completion_token": 0.0042
    },
    "gpt-4-0613": {
        "prompt_token": 0.21,
        "completion_token": 0.42
    },
    "gpt-4-turbo-preview": {
        "prompt_token": 0.07,
        "completion_token": 0.21
    },
    "gpt-4-0125-preview": {
        "prompt_token": 0.07,
        "completion_token": 0.21
    },
    "gpt-4-1106-preview": {
        "prompt_token": 0.07,
        "completion_token": 0.21
    },
    "gpt-4-vision-preview": {
        "prompt_token": 0.07,
        "completion_token": 0.21
    },
    "gpt-4-turbo": {
        "prompt_token": 0.07,
        "completion_token": 0.21
    },
    "gpt-4-turbo-2024-04-09": {
        "prompt_token": 0.07,
        "completion_token": 0.21
    },
    "gpt-3.5-turbo-ca": {
        "prompt_token": 0.001,
        "completion_token": 0.003
    },
    "gpt-4-ca": {
        "prompt_token": 0.12,
        "completion_token": 0.24
    },
    "gpt-4-turbo-ca": {
        "prompt_token": 0.04,
        "completion_token": 0.12
    },
    "gpt-4o-ca": {
        "prompt_token": 0.01,
        "completion_token": 0.04
    },
    "chatgpt-4o-latest-ca": {
        "prompt_token": 0.02,
        "completion_token": 0.06
    },
    "o1-mini-ca": {
        "prompt_token": 0.012,
        "completion_token": 0.048
    },
    "o1-preview-ca": {
        "prompt_token": 0.06,
        "completion_token": 0.24
    },
    "claude-3-5-sonnet-20240620": {
        "prompt_token": 0.015,
        "completion_token": 0.075
    },
    "claude-3-5-sonnet-20241022": {
        "prompt_token": 0.015,
        "completion_token": 0.075
    },
    "claude-3-5-haiku-20241022": {
        "prompt_token": 0.005,
        "completion_token": 0.025
    },
    "gemini-1.5-flash-latest": {
        "prompt_token": 0.0006,
        "completion_token": 0.0024
    },
    "gemini-1.5-pro-latest": {
        "prompt_token": 0.01,
        "completion_token": 0.04
    },
    "gemini-exp-1206": {
        "prompt_token": 0.01,
        "completion_token": 0.04
    },
    "gemini-2.0-flash-exp": {
        "prompt_token": 0.01,
        "completion_token": 0.04
    }
}


class Message:
    def __init__(self, role, content):
        self.role = role
        self.content = content
        self.token_num = 0
        self.token_cost = 0

    def to_openai_message(self):
        return {"role": self.role, "content": self.content}

    def __str__(self):
        return self.content

    def __repr__(self):
        return f"'{self.role}, {self.token_num}, {self.token_cost}'"


class SystemMessage(Message):
    def __init__(self, content):
        super().__init__("system", content)


class UserMessage(Message):
    def __init__(self, content):
        super().__init__("user", content)


class AssistantMessage(Message):
    def __init__(self, content):
        super().__init__("assistant", content)


class OpenAIMessage(Message):
    def __init__(self, content, model, openai_usage: CompletionUsage):
        super().__init__("assistant", content)

        self.model = model
        self.openai_usage = openai_usage
        self.prompt_token_num = openai_usage.prompt_tokens
        self.prompt_token_cost = model_cost[self.model]["prompt_token"] * self.prompt_token_num / 1000
        self.completion_token_num = openai_usage.completion_tokens
        self.completion_token_cost = model_cost[self.model]["completion_token"] * self.completion_token_num / 1000
        self.token_num = self.prompt_token_num + self.completion_token_num
        self.token_cost = self.prompt_token_cost + self.completion_token_cost
