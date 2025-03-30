from agent_network.network.executable import Executable
from agent_network.utils.task import get_task_type
from agent_network.task.task_call import TaskStatus


class TaskVertex:
    def __init__(self, executable: Executable = None, task=None, id=None, status=TaskStatus.NEW.value, token=0, token_cost=0,
                 time_cost=0, type=None):
        self.task = task
        self.executable = executable
        try:
            self.id = id if id else self.executable.name
        except:
            try:
                print(f"{self.executable.id}")
            except:
                print(f"{self.executable} id not exist")
                pass
        self.status = status
        self.token = token
        self.token_cost = token_cost
        self.time_cost = time_cost
        self.type = type if type is not None else get_task_type(executable)

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

    def get_type(self):
        return self.type
