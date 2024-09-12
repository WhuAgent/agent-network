from agent_network.pipeline.executable import Executable
import agent_network.pipeline.context as ctx
from agent_network.base import BaseAgent
import threading


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
                ctx.register_global(self.executable.name, result)
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
        if not self.next_executables or len(self.next_executables) == 0:
            raise Exception("GroupNode do not have executables")
        group_threads = []
        for next_executable in self.next_executables:
            group_thread = threading.Thread(
                target=lambda ne=next_executable, ic=input_content: ne.execute(ic)
            )
            group_threads.append(group_thread)
            group_thread.start()
        for group_thread in group_threads:
            group_thread.join()


class TaskNode(Node):
    def __init__(self, next_executables: [Executable], name, task):
        super().__init__(Executable("TaskNode", "TaskNode"), next_executables)
        self.name = name
        self.task = task

    def execute(self, input_content):
        if not self.next_executables or len(self.next_executables) == 0:
            raise Exception("TaskNode do not have executables")
        for next_executable in self.next_executables:
            next_executable.execute(input_content)
        task_threads = []
        for next_executable in self.next_executables:
            task_thread = threading.Thread(
                target=lambda ne=next_executable, ic=input_content: ne.execute(ic)
            )
            task_threads.append(task_thread)
            task_thread.start()
        for task_thread in task_threads:
            task_thread.join()
