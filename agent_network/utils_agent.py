import numpy as np
from base import BaseAgent


class ScoreAgent(BaseAgent):

    def __init__(self, logger, score_demand):
        demand = "请对以下基于需求由多个不同的智能体响应的结果列表进行评分，评分越高说明该智能体的响应结果越能够满足需求"
        super().__init__(logger, demand)
        self.score_demand = score_demand

    def initial_messages(self, current_demand):
        messages = [
            {"role": "system", "content": f"你是一个智能体间协作评分智能体，用于给下游智能体返回的结果打分，当前的需求为：{self.score_demand}，直接返回一个评分列表"},
            {"role": "user", "content": "当前下游多个智能体的结果列表如下: " + current_demand}
        ]
        return messages

    def execute(self, response_content):
        return np.argsort(list(response_content))[::-1], None
