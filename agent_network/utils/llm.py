import os

from openai import OpenAI
from openai.types.completion_usage import CompletionUsage


model_cost = {
    "gpt-3.5-turbo": {
        "prompt_token": 0.0035,
        "completion_token": 0.0105
    }
}


class Usage:
    def __init__(self, model: str, openai_usage: CompletionUsage):
        self.model = model
        self.prompt_token = openai_usage.prompt_tokens
        self.prompr_cost = model_cost[model]["prompt_token"] * self.prompt_token / 1000
        self.completion_token = openai_usage.completion_tokens
        self.completion_cost = model_cost[model]["completion_token"] * self.completion_token / 1000
        self.total_token = self.prompt_token + self.completion_token
        self.total_cost = self.prompr_cost + self.completion_cost


def chat_llm(model, messages, **kwargs):
    openai_client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1/")
    )
    response = openai_client.chat.completions.create(
        messages=messages,
        model=model,
        **kwargs
    )
    return response.choices[0].message, Usage(model, response.usage)