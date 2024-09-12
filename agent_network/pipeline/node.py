from agent_network.pipeline.executable import Executable
from agent_network.base import BaseAgent


class Node(Executable):
    def __init__(self, executable: Executable, next_executables: [Executable]):
        super().__init__(executable.name, executable.task)
        self.name = executable.name
        self.executable = executable
        self.next_executables = next_executables

    def execute(self, input_content):
        # an agent chain runs sequentially with sharing context
        if isinstance(self.executable, BaseAgent):
            result = self.executable.agent_base(input_content)
            if self.next_executables:
                for next_executable in self.next_executables:
                    if isinstance(next_executable, BaseAgent):
                        next_executable.agent_base(result)
                    else:
                        next_executable.execute(result)
        else:
            result = self.executable.execute(input_content)
            if self.next_executables:
                for next_executable in self.next_executables:
                    next_executable.execute(result)


class GroupNode(Node):
    def __init__(self, next_executables: [Executable], group_name, group_task):
        super().__init__(Executable("GroupNode", "GroupNode"), next_executables)
        self.group_name = group_name
        self.group_task = group_task

    def execute(self, input_content):
        # todo agents run parallel with a group
        if not self.next_executables or len(self.next_executables) == 0:
            raise Exception("GroupNode do not have executables")
        for next_executable in self.next_executables:
            next_executable.execute(input_content)


class TaskNode(Node):
    def __init__(self, next_executables: [Executable], name, task):
        super().__init__(Executable("TaskNode", "TaskNode"), next_executables)
        self.name = name
        self.task = task

    def execute(self, input_content):
        # todo groups run parallel with a task
        if not self.next_executables or len(self.next_executables) == 0:
            raise Exception("TaskNode do not have executables")
        for next_executable in self.next_executables:
            next_executable.execute(input_content)
