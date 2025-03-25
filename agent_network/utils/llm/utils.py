import os
import yaml

llm_config_path = os.path.join(os.getcwd(), 'config/llm.yaml')
with open(llm_config_path, "r", encoding="UTF-8") as f:
    llm_config = yaml.safe_load(f)


def get_model_family(model):
    if "openai" in model or "gpt" in model:
        return "openai"
    if "deepseek" in model:
        return "deepseek"
    if "qwen" in model or "qwq" in model:
        return "qwen"


def get_api_key(**kwargs):
    if "api_key" in kwargs.keys():
        api_key = kwargs.get("api_key")
    else:
        model_family = get_model_family(get_model(**kwargs))
        api_key = llm_config.get(model_family).get("api_key", os.getenv("OPENAI_API_KEY"))

    return api_key


def get_base_url(**kwargs):
    if "base_url" in kwargs.keys():
        base_url = kwargs.get("base_url")
    else:
        model_family = get_model_family(get_model(**kwargs))
        base_url = llm_config.get(model_family).get("base_url",
                                                    os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1/"))

    return base_url


def get_model(**kwargs):
    if "model" in kwargs.keys():
        model = kwargs.get("model")
    else:
        model = llm_config.get("default_model", os.getenv("OPENAI_MODEL"))

    return model
