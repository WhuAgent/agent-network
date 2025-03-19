import json

from agent_network.base import BaseAgent

class AgentNetworkPlanner(BaseAgent):
    def __init__(self, graph, config, logger):
        super().__init__(graph, config, logger)
        
    def forward(self, messages, **kwargs):
        task = kwargs.get("task")
        
        prompt = f"现在用户的需求是：{task}"
        
        self.add_message("user", prompt, messages)
        
        response = self.chat_llm(messages, json_response=True)
        
        sub_tasks = response.content
        
        if isinstance(sub_tasks, dict):
            sub_tasks = sub_tasks.get("tasks")
            
        for i in range(len(sub_tasks)):
            if i == len(sub_tasks) - 1:
                sub_tasks[i]["next"] = [-1]
            else:
                sub_tasks[i]["next"] = [i + 1]
        
        results = {
            "sub_tasks": sub_tasks,
            "step": -1
        }
        
        return results
    

class AgentNetworkSummarizer(BaseAgent):
    def __init__(self, graph, config, logger):
        super().__init__(graph, config, logger)
        
    def forward(self, messages, **kwargs):
        task = kwargs.pop("task")
        
        prompt = f"现在用户的任务是：\n{task}\n\n在智能体网络完成任务的过程中，产生了如下上下文信息：\n{kwargs}\n\n请对该任务的执行结果进行总结。"
        
        self.add_message("user", prompt, messages)
        
        response = self.chat_llm(messages, json_response=True)
        
        results = response.content
        
        return results