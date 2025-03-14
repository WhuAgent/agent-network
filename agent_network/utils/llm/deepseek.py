import requests
import re

from agent_network.utils.llm.utils import get_api_key, get_base_url, get_model
from agent_network.utils.llm.message import Message, DeepSeekMessage

API_KEY = "sk-ca3583e3026949299186dcbf3fc34f8c"
BASE_URL = "https://api.deepseek.com"


def chat_llm(messages: list[Message], **kwargs):
    api_key, kwargs = get_api_key(**kwargs)
    base_url, kwargs = get_base_url(**kwargs)
    model, kwargs = get_model(**kwargs)

    deepseek_messages = []
    for message in messages:
        deepseek_messages.append(message.to_openai_message())

    url = f"{base_url}/chat/completions"
    payload = {
        "model": model,
        "messages": deepseek_messages,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    response = requests.request("POST", url, json=payload, headers=headers)
    
    if "504 Gateway Time-out" in response.text:
        return DeepSeekMessage("The problem takes too long to solve.", "I don't know.", model, {"prompt_tokens": 0, "completion_tokens": 0})
    else:
        response = response.json()

        return DeepSeekMessage(response["choices"][0]["message"]["reasoning_content"],
                            response["choices"][0]["message"]["content"], 
                            model, 
                            response["usage"])
    

def chat_llm_local(messages: list[Message], **kwargs):
    api_key, kwargs = get_api_key(**kwargs)
    base_url, kwargs = get_base_url(**kwargs)
    model, kwargs = get_model(**kwargs)

    deepseek_messages = []
    for message in messages:
        deepseek_messages.append(message.to_openai_message())

    url = f"{base_url}/chat/completions"
    payload = {
        "model": model,
        "messages": deepseek_messages,
        "max_tokens": 10000
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    response = requests.request("POST", url, json=payload, headers=headers)
    
    if "504 Gateway Time-out" in response.text:
        return DeepSeekMessage("The problem takes too long to solve.", "I don't know.", model, {"prompt_tokens": 0, "completion_tokens": 0})
    else:
        response = response.json()

        content = response["choices"][0]["message"]["content"]

        # 提取 <think> 和 </think> 之间的内容（包括换行符）
        think_match = re.search(r'<think>(.*?)</think>', content, re.DOTALL | re.IGNORECASE)
        reasoning_content = think_match.group(1).strip() if think_match else ""
        
        # 提取 </think> 之后的所有内容作为回答
        answer_content = content[think_match.end():].strip() if think_match else ""

        return DeepSeekMessage(reasoning_content,
                               answer_content, 
                               model, 
                               response["usage"])