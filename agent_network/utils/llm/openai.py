import os
import yaml
from openai import OpenAI
from agent_network.utils.llm.message import Message, OpenAIMessage, model_cost

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

    if model not in model_cost:
        raise Exception(f"model: {model} is invalid.")
    openai_messages = []
    for message in messages:
        openai_messages.append(message.to_openai_message())

    if "stream" in model_cost[model] and model_cost[model]["stream"]:
        kwargs["stream"] = True
        kwargs["stream_options"] = {"include_usage": True}
    response = openai_client.chat.completions.create(
        messages=openai_messages,
        model=model,
        seed=42,
        **kwargs,
    )
    response_text = ""
    prompt_tokens = 0
    completion_tokens = 0
    if "stream" in kwargs and kwargs["stream"]:
        for chunk in response:
            if len(chunk.choices) > 0 and chunk.choices[0].delta.content:
                response_text += chunk.choices[0].delta.content
                if chunk.usage:
                    prompt_tokens += chunk.usage.prompt_tokens
                    completion_tokens += chunk.usage.completion_tokens
    else:
        response_text = response.choices[0].message.content
        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = response.usage.completion_tokens

    return OpenAIMessage(response_text, model, prompt_tokens, completion_tokens)
