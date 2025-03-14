from agent_network.network.executable import Executable


class TaskNode:
    def __init__(self, executable: Executable=None, message=None, task=None, name=None):
        self.task = task
        self.message = message
        self.executable = executable
        self.name = name if name else self.executable.name
