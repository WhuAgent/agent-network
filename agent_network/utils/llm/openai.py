import urequests
import ujson
from agent_network.utils.llm.message import Message, OpenAIMessage, model_cost

# openai_config_path = mp.path_join(os.getcwd(), 'config/openai.yml')
# with open(openai_config_path, "r", encoding="UTF-8") as f:
#     openai_config = yaml.safe_load(f)


def chat_llm(messages: list[Message], model=None, **kwargs):
    # if model is None:
    #     model = openai_config.get("model", os.getenv("OPENAI_MODEL"))
    if model not in model_cost:
        raise Exception(f"model: {model} is invalid.")
    openai_messages = []
    for message in messages:
        openai_messages.append(message.to_openai_message())
    api_key = "sk-uz2K0lhafPFynE77BBX5v0adDXDzxJWir05jrlPCPQoMslp9",
    base_url = "https://api.openai.com/v1/"
    # 创建请求头
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    # openai_client = OpenAI(
    #     api_key=openai_config.get("api_key", os.getenv("OPENAI_API_KEY")),
    #     base_url=openai_config.get("base_url", os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1/")),
    # )
    data = {
        "model": model,
        "messages": openai_messages,
        "temperature": 0.7,
        "max_tokens": 1000,
        "seed": 42
    }
    response = urequests.post(base_url, json=data, headers=headers)

    # if "stream" in model_cost[model] and model_cost[model]["stream"]:
    #     kwargs["stream"] = True
    #     kwargs["stream_options"] = {"include_usage": True}
    # 处理响应
    response_text = ""
    if response.status_code == 200:
        result = ujson.loads(response.text)
        response_text = result["choices"][0]["message"]["content"]
        print(response_text)
    else:
        print("Error:", response.status_code)

    # 关闭响应
    response.close()
    prompt_tokens = 0
    completion_tokens = 0
    # if "stream" in kwargs and kwargs["stream"]:
    #     for chunk in response:
    #         if len(chunk.choices) > 0 and chunk.choices[0].delta.content:
    #             response_text += chunk.choices[0].delta.content
    #             if chunk.usage:
    #                 prompt_tokens += chunk.usage.prompt_tokens
    #                 completion_tokens += chunk.usage.completion_tokens
    # else:
    #     response_text = response.choices[0].message.content
    #     prompt_tokens = response.usage.prompt_tokens
    #     completion_tokens = response.usage.completion_tokens

    return OpenAIMessage(response_text, model, prompt_tokens, completion_tokens)
