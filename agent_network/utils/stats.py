def usage_calculate(usages, time_costs, begin_timestamp, end_timestamp):
    total_usage = {
        "completion_tokens": 0,
        "prompt_tokens": 0,
        "total_tokens": 0
    }
    total_time = 0
    for usage in usages:
        if begin_timestamp <= usage.timestamp <= end_timestamp:
            total_usage['completion_tokens'] += usage.completion_token
            total_usage['prompt_tokens'] += usage.prompt_tokens
            total_usage['total_tokens'] += usage.total_tokens
    for time_cost in time_costs:
        if begin_timestamp <= time_cost.timestamp <= end_timestamp:
            total_time += time_cost.usage_time
    return total_usage, total_time


def usage_calculate_all(usages, time_costs):
    total_usage = {
        "completion_tokens": 0,
        "prompt_tokens": 0,
        "total_tokens": 0
    }
    total_time = 0
    for usage in usages:
        total_usage['completion_tokens'] += usage.completion_token
        total_usage['prompt_tokens'] += usage.prompt_tokens
        total_usage['total_tokens'] += usage.total_tokens
    for time_cost in time_costs:
        total_time += time_cost.usage_time
    return total_usage, total_time
