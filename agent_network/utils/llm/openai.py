from openai import OpenAI

import json

from agent_network.utils.llm.utils import get_api_key, get_base_url, get_model
from agent_network.utils.llm.message import Message, OpenAIMessage


def chat_llm(messages: list[Message], **kwargs):
    api_key, kwargs = get_api_key(**kwargs)
    base_url, kwargs = get_base_url(**kwargs)
    model, kwargs = get_model(**kwargs)
    
    openai_client = OpenAI(api_key=api_key, base_url=base_url)

    openai_messages = []
    for message in messages:
        openai_messages.append(message.to_openai_message())

    response = openai_client.chat.completions.create(
        messages=openai_messages,
        model=model,
        **kwargs
    )
    
    if kwargs.get("response_format") == {"type": "json_object"}:
        response_content = json.loads(response.choices[0].message.content)
    else:
        response_content = response.choices[0].message.content

    return OpenAIMessage(response_content, model, response.usage)
