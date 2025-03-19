import os
import yaml
import json
from openai import OpenAI
from agent_network.utils.llm.message import Message, OpenAIMessage, model_cost
from agent_network.utils.llm.utils import get_api_key, get_base_url, get_model


def remove_unnecessary_keys(**kwargs):
    keys = ["api_key", "base_url", "model"]
    for key in keys:
        if key in kwargs.keys():
            del kwargs[key]
    return kwargs

def chat_llm_json(messages: list[Message], **kwargs):
    kwargs["response_format"] = {"type": "json_object"}
    return chat_llm(messages, **kwargs)
    

def chat_llm(messages: list[Message], **kwargs):
    api_key = get_api_key(**kwargs)
    base_url = get_base_url(**kwargs)
    model = get_model(**kwargs)
    kwargs = remove_unnecessary_keys(**kwargs)
    
    openai_client = OpenAI(api_key=api_key, base_url=base_url)

    openai_messages = []
    for message in messages:
        openai_messages.append(message.to_openai_message())

    response = openai_client.chat.completions.create(
        messages=openai_messages,
        model=model,
        **kwargs
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
    
    if kwargs.get("response_format") == {"type": "json_object"}:
        response_text = json.loads(response_text)

    return OpenAIMessage(response_text, model, prompt_tokens, completion_tokens)