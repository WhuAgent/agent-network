from agent_network.network.executable import Executable


class TaskVertex:
    def __init__(self, executable: Executable=None, task=None, id=None):
        self.task = task
        self.executable = executable
        self.id = id if id else self.executable.id
