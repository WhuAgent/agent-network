import os
import yaml
from openai import OpenAI
from openai.types.completion_usage import CompletionUsage

openai_config_path = os.path.join(os.getcwd(), 'agent_network/config/openai.yml')
with open(openai_config_path, "r", encoding="UTF-8") as f:
    openai_config = yaml.safe_load(f)

model_cost = {
    "gpt-3.5-turbo": {
        "prompt_token": 0.0035,
        "completion_token": 0.0105
    },
    "gpt-4": {
        "prompt_token": 0.21,
        "completion_token": 0.42
    }
}


class Usage:
    def __init__(self, model: str, openai_usage: CompletionUsage):
        self.model = model
        self.prompt_tokens = openai_usage.prompt_tokens
        self.prompt_cost = model_cost[model]["prompt_token"] * self.prompt_tokens / 1000
        self.completion_tokens = openai_usage.completion_tokens
        self.completion_cost = model_cost[model]["completion_token"] * self.completion_tokens / 1000
        self.total_tokens = openai_usage.total_tokens
        self.total_cost = self.prompt_cost + self.completion_cost


def chat_llm(messages, model=None, **kwargs):
    if model is None:
        model = openai_config.get("model", os.getenv("OPENAI_MODEL"))
    openai_client = OpenAI(
        api_key=openai_config.get("api_key", os.getenv("OPENAI_API_KEY")),
        base_url=openai_config.get("base_url", os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1/")),
    )
    response = openai_client.chat.completions.create(
        messages=messages,
        model=model,
        **kwargs
    )
    return response.choices[0].message, Usage(model, response.usage)
