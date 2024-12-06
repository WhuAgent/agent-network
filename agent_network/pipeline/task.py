from agent_network.network.executable import Executable


class TaskNode:
    def __init__(self, executable: Executable, task):
        self.task = task
        self.executable = executable
        self.name = self.executable.name
