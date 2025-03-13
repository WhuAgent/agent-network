from agent_network.graph.task_vertex import TaskVertex
from agent_network.utils.llm.message import Message


class History:
    def __init__(self, pre_executors, cur_executor):
        self.pre_executors: list[TaskVertex] = pre_executors
        self.cur_executor: TaskVertex = cur_executor
        self.next_executors: list[TaskVertex] = None

        self.llm_messages: list[Message] = []

        self.time_cost = 0
