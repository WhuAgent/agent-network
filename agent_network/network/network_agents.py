from agent_network.base import BaseAgent
from agent_network.network.vertexes.graph_vertex import GroupVertex, ThirdPartyGroupVertex


class AgentNetworkPlanner(BaseAgent):
    def __init__(self, network, config, logger):
        super().__init__(network, config, logger)
        self.network = network

    def forward(self, messages, **kwargs):
        task = kwargs.get("task")

        prompt = f"现在用户的需求是：{task}"

        self.add_message("user", prompt, messages)

        vertexs = []
        for vertex_name, vertex in self.network.vertexes.items():
            if vertex_name == "AgentNetworkPlannerGroup/AgentNetworkPlanner" or vertex_name == "AgentNetworkSummarizerGroup/AgentNetworkSummarizer":
                continue
            # 只感知 group
            if isinstance(vertex, GroupVertex) or isinstance(vertex, ThirdPartyGroupVertex):
                vertexs.append(f"{vertex_name}: {vertex.description}")
        agents_description = "\n".join(vertexs)
        agents_prompt = f"### 团队成员 ###\n你的团队中有以下成员：\n\n{agents_description}\n\n### 目标 ###\n给定用户需求，你需要理解用户需求，并根据团队中成员的能力，为团队成员分配任务，形成一个可以完成用户需求的工作流。\n\n### 返回方式 ###\n请以 JSON 方式返回一个子任务列表，列表中的每一项包含两个字段：\n\ntask: 任务名称；\nexecutor: 执行任务的成员；\n\n### 返回示例 ###\n[\n    {{\n        \"task\": \"...\",\n        \"executor\": \"...\",\n    }},\n    {{\n        \"...\"\n    }}\n]\n"

        self.add_message("user", agents_prompt, messages)

        response = self.chat_llm(messages, json_response=True)

        sub_tasks = response.content

        if isinstance(sub_tasks, dict):
            if "tasks" in sub_tasks:
                sub_tasks = sub_tasks.get("tasks")
            elif "subTasks" in sub_tasks:
                sub_tasks = sub_tasks.get("subTasks")
            elif "subtasks" in sub_tasks:
                sub_tasks = sub_tasks.get("subtasks")
            elif "sub_tasks" in sub_tasks:
                sub_tasks = sub_tasks.get("sub_tasks")
            elif "taskList" in sub_tasks:
                sub_tasks = sub_tasks.get("taskList")
            elif "task_list" in sub_tasks:
                sub_tasks = sub_tasks.get("task_list")

        if sub_tasks is None:
            raise Exception("Planner's subTasks are None.")
        results = {
            "sub_tasks": sub_tasks
        }

        return results


class AgentNetworkSummarizer(BaseAgent):
    def __init__(self, network, config, logger):
        super().__init__(network, config, logger)

    def forward(self, messages, **kwargs):
        task = kwargs.pop("task")
        execution_graph = kwargs.get("executionGraph")

        prompt = f"现在用户的任务是：\n{task}\n\n在智能体网络完成任务的过程中，产生了如下全过程执行图\n{execution_graph}，产生了如下上下文信息：\n{kwargs}\n\n请对该任务的执行结果进行总结。"

        self.add_message("user", prompt, messages)

        response = self.chat_llm(messages, json_response=True)

        results = response.content

        return results
