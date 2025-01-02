from agent_network.pipeline.task import TaskNode
from agent_network.utils.llm.message import Message

class History:
    def __init__(self, pre_executors, cur_executor):
        self.pre_executors: list[TaskNode] = pre_executors
        self.cur_executor: TaskNode = cur_executor
        self.next_executors: list[TaskNode] = None

        self.llm_messages: list[Message] = []

        self.time_cost = 0
