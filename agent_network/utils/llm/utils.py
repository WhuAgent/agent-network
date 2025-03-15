import os
import yaml


openai_config_path = os.path.join(os.getcwd(), 'config/openai.yml')
with open(openai_config_path, "r", encoding="UTF-8") as f:
    openai_config = yaml.safe_load(f)


def get_api_key(**kwargs):
    if "api_key" in kwargs.keys():
        api_key = kwargs.pop("api_key")
    else:
        api_key = openai_config.get("api_key", os.getenv("OPENAI_API_KEY"))
    
    return api_key, kwargs


def get_base_url(**kwargs):
    if "base_url" in kwargs.keys():
        base_url = kwargs.pop("base_url")
    else:
        base_url = openai_config.get("base_url", os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1/"))
    
    return base_url, kwargs
    

def get_model(**kwargs):
    if "model" in kwargs.keys():
        model = kwargs.pop("model")
    else:
        model = openai_config.get("model", os.getenv("OPENAI_MODEL"))

    return model, kwargs