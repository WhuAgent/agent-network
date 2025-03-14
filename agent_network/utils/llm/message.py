from openai.types.completion_usage import CompletionUsage

model_cost = {
    "gpt-3.5-turbo": {
        "prompt_token": 0.0035,
        "completion_token": 0.0105
    },
    "o1-mini": {
        "prompt_token": 0.021,
        "completion_token": 0.084
    },
    "gpt-4": {
        "prompt_token": 0.21,
        "completion_token": 0.42
    },
    "deepseek-chat": {
        "prompt_token": 0.002,
        "completion_token": 0.008
    },
    "Pro/deepseek-ai/DeepSeek-R1": {
        "prompt_token": 0.004,
        "completion_token": 0.016
    },
    "deepseek-ai/DeepSeek-R1-Distill-Llama-70B": {
        "prompt_token": 0.00413,
        "completion_token": 0.00413
    },
    "deepseek-r1:14b": {
        "prompt_token": 0.004,
        "completion_token": 0.016
    },
    "deepseek-r1:7b": {
        "prompt_token": 0.004,
        "completion_token": 0.016
    }
}


class Message:
    def __init__(self, role, content):
        self.role = role
        self.content = content
        self.token_num = 0
        self.token_cost = 0

    def to_openai_message(self):
        return {"role": self.role, "content": str(self.content)}

    def __str__(self):
        return self.content

    def __repr__(self):
        return f"{self.__class__.__name__}({self.content})"


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
        self.prompt_token_num = openai_usage.prompt_tokens
        self.prompt_token_cost = model_cost[self.model]["prompt_token"] * self.prompt_token_num / 1000
        self.completion_token_num = openai_usage.completion_tokens
        self.completion_token_cost = model_cost[self.model]["completion_token"] * self.completion_token_num / 1000
        self.token_num = self.prompt_token_num + self.completion_token_num
        self.token_cost = self.prompt_token_cost + self.completion_token_cost


class DeepSeekMessage(Message):
    def __init__(self, resoning_content, content, model, deepseek_usage):
        super().__init__("assistant", content)

        self.resoning_content = resoning_content

        self.model = model
        self.prompt_token_num = deepseek_usage["prompt_tokens"]
        self.prompt_token_cost = model_cost[self.model]["prompt_token"] * self.prompt_token_num / 1000
        self.completion_token_num = deepseek_usage["completion_tokens"]
        self.completion_token_cost = model_cost[self.model]["completion_token"] * self.completion_token_num / 1000
        self.token_num = self.prompt_token_num + self.completion_token_num
        self.token_cost = self.prompt_token_cost + self.completion_token_cost

