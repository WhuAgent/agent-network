import os
import yaml
from openai import OpenAI

from agent_network.utils.llm.message import Message, OpenAIMessage

openai_config_path = os.path.join(os.getcwd(), 'config/openai.yml')
with open(openai_config_path, "r", encoding="UTF-8") as f:
    openai_config = yaml.safe_load(f)


def chat_llm(messages: list[Message], model=None, **kwargs):
    if model is None:
        model = openai_config.get("model", os.getenv("OPENAI_MODEL"))
    openai_client = OpenAI(
        api_key=openai_config.get("api_key", os.getenv("OPENAI_API_KEY")),
        base_url=openai_config.get("base_url", os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1/")),
    )

    openai_messages = []
    for message in messages:
        openai_messages.append(message.to_openai_message())

    response = openai_client.chat.completions.create(
        messages=openai_messages,
        model=model,
        seed=42,
        **kwargs
    )

    return OpenAIMessage(response.choices[0].message.content, model, response.usage)
