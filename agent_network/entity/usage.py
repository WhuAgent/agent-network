class UsageToken:
    def __init__(self, timestamp, usage_token_map):
        self.timestamp = timestamp
        self.completion_tokens = usage_token_map["completion_tokens"]
        self.prompt_tokens = usage_token_map["prompt_tokens"]
        self.total_tokens = usage_token_map["total_tokens"]
        self.prompt_cost = usage_token_map["prompt_cost"]
        self.completion_cost = usage_token_map["completion_cost"]
        self.total_cost = usage_token_map["total_cost"]


class UsageTime:
    def __init__(self, timestamp, usage_time):
        self.timestamp = timestamp
        self.usage_time = usage_time
