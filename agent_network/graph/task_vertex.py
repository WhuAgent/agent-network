from agent_network.network.executable import Executable

from agent_network.task.task_call import TaskStatus


class TaskVertex:
    def __init__(self, executable: Executable=None, task=None, id=None):
        self.task = task
        self.executable = executable
        self.id = id if id else self.executable.name
        self.status = TaskStatus.NEW
        self.token = 0
        self.token_cost = 0
        self.time_cost = 0

    def get_task(self):
        return self.task

    def get_status(self):
        return self.status

    def set_status(self, status):
        self.status = status

    def get_token(self):
        return self.token

    def get_token_cost(self):
        return self.token_cost

    def get_time_cost(self):
        return self.time_cost
