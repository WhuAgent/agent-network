from abc import abstractmethod
from agent_network.base import BaseAgent


class Executable:
    def __init__(self, name, task, **kwargs):
        self.name = name
        self.task = task
        self.context = {**kwargs}

    def post_init_inner(self, context):
        self.shared_context(context)
        self.post_init(context)

    @abstractmethod
    def post_init(self, context):
        pass

    @abstractmethod
    def execute(self, input_content):
        pass

    def register(self, key, value):
        self.context[key] = value

    def retrieve(self, key):
        if key not in self.context:
            raise Exception(f"context do not contain key: {key}")
        return self.context[key]

    def shared_context(self, context):
        self.context = {**self.context, **context}


class Node(Executable):
    def __init__(self, executable: Executable, nextExecutables: [Executable]):
        super().__init__(executable.name, executable.task)
        self.name = executable.name
        self.executable = executable
        self.nextExecutables = nextExecutables

    def execute(self, input_content):
        # an agent chain runs sequentially with sharing context
        if isinstance(self.executable, BaseAgent):
            result = self.executable.agent(self.executable.runtime_revision_number, input_content)
            if self.nextExecutables:
                for nextExecutable in self.nextExecutables:
                    nextExecutable.shared_context(self.context)
                    if isinstance(nextExecutable, BaseAgent):
                        nextExecutable.agent(nextExecutable.runtime_revision_number, result)
                    else:
                        nextExecutable.execute(result)
        else:
            result = self.executable.execute(input_content)
            if self.nextExecutables:
                for nextExecutable in self.nextExecutables:
                    nextExecutable.shared_context(self.context)
                    nextExecutable.execute(result)

    def post_init(self, context):
        pass


class GroupNode(Node):
    def __init__(self, nextExecutables: [Executable], group_name, group_task):
        super().__init__(Executable("GroupNode", "GroupNode"), nextExecutables)
        self.group_name = group_name
        self.group_task = group_task

    def execute(self, input_content):
        # todo agents run parallel with a group
        if not self.nextExecutables or len(self.nextExecutables) == 0:
            raise Exception("GroupNode do not have executables")
        for nextExecutable in self.nextExecutables:
            nextExecutable.shared_context(self.context)
            nextExecutable.execute(input_content)


class TaskNode(Node):
    def __init__(self, nextExecutables: [Executable], name, task):
        super().__init__(Executable("TaskNode", "TaskNode"), nextExecutables)
        self.name = name
        self.task = task

    def execute(self, input_content):
        # todo groups run parallel with a task
        if not self.nextExecutables or len(self.nextExecutables) == 0:
            raise Exception("TaskNode do not have executables")
        for nextExecutable in self.nextExecutables:
            nextExecutable.shared_context(self.context)
            nextExecutable.execute(input_content)
