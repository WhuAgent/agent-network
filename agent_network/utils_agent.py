import numpy as np
from base import BaseAgent


class ScoreAgent(BaseAgent):
    def __init__(self, logger, title, task, role, description, history_number):
        self.template_task = f"你是一个智能体间协作评分智能体，用于给下游智能体返回的结果打分，请对以下基于需求由多个不同的智能体响应的结果列表进行评分，评分越高说明该智能体的响应结果越能够满足需求，" \
                             f"当前的需求为：{self.task}，直接返回一个评分列表[,]"
        super().__init__(logger, title, task, role, description, history_number, None, None, 0)

    def initial_messages(self, current_task):
        messages = [
            {"role": "system", "content": self.template_task},
            {"role": "user", "content": "当前下游多个智能体的结果列表如下: " + current_task}
        ]
        return messages

    def execute(self, response_content):
        return np.argsort(list(response_content))[::-1], None
