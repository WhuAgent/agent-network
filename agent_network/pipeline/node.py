from abc import abstractmethod


class Executable:
    def __init__(self, name, task):
        self.name = name
        self.task = task

    @abstractmethod
    def execute(self, input_content):
        pass


class Node(Executable):
    def __init__(self, executable: Executable, nextExecutables: [Executable]):
        super().__init__(executable.name, executable.task)
        self.name = executable.name
        self.executable = executable
        self.nextExecutables = nextExecutables

    def execute(self, input_content):
        result = self.executable.execute(input_content)
        if self.nextExecutables:
            for nextExecutable in self.nextExecutables:
                nextExecutable.execute(result)


class GroupNode(Node):
    def __init__(self, nextExecutables: [Executable], group_name, group_task):
        super().__init__(Executable("GroupNode", "GroupNode"), nextExecutables)
        self.group_name = group_name
        self.group_task = group_task

    def execute(self, input_content):
        if not self.nextExecutables or len(self.nextExecutables) == 0:
            raise Exception("GroupNode do not have executables")
        for nextExecutable in self.nextExecutables:
            nextExecutable.execute(input_content)


class TaskNode(Node):
    def __init__(self, nextExecutables: [Executable], name, task):
        super().__init__(Executable("TaskNode", "TaskNode"), nextExecutables)
        self.name = name
        self.task = task

    def execute(self, input_content):
        if not self.nextExecutables or len(self.nextExecutables) == 0:
            raise Exception("TaskNode do not have executables")
        for nextExecutable in self.nextExecutables:
            nextExecutable.execute(input_content)
