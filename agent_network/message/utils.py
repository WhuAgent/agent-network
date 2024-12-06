from openai import OpenAI
import os
import yaml

openai_config_path = os.path.join(os.getcwd(), 'agent_network/message/config/openai.yml')
with open(openai_config_path, "r", encoding="UTF-8") as f:
    openai_config = yaml.safe_load(f)


def chat_llm(messages):
    openai_client = OpenAI(
        api_key=openai_config["api_key"],
        base_url=openai_config["base_url"]
    )
    response = openai_client.chat.completions.create(
        messages=messages,
        model="gpt-3.5-turbo",
        temperature=0.2
    )
    return response.choices[0].message, response.usage
