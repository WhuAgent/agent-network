from agent_network.pipeline.executable import Executable
import agent_network.pipeline.context as ctx
from agent_network.base import BaseAgent
import threading


class Node(Executable):
    def __init__(self, executable: Executable, next_executables: [Executable], params, results):
        super().__init__(executable.name, executable.task, params, results)
        self.name = executable.name
        self.executable = executable
        self.next_executables = next_executables

    def execute(self, input_content):
        # an agent chain runs sequentially with sharing context
        return_next_task = None
        if isinstance(self.executable, BaseAgent):
            next_task, results = self.executable.agent_base(
                input_content if not input_content else self.executable.task,
                **ctx.retrieves([param["name"] for param in self.params]))
            ctx.registers(results)
            if self.next_executables:
                for next_executable in self.next_executables:
                    next_task = next_executable.execute(next_task)
                    return_next_task = next_task
            else:
                return_next_task = next_task
                ctx.registers_global(ctx.retrieves([result["name"] for result in self.results]))
        else:
            next_task = self.executable.execute(input_content if not input_content else self.executable.task)
            if self.next_executables:
                for next_executable in self.next_executables:
                    next_task = next_executable.execute(next_task)
                    return_next_task = next_task
            else:
                return_next_task = next_task
        return return_next_task


class GroupNode(Node):
    def __init__(self, next_executables: [Executable], group_name, group_task, params, results):
        super().__init__(Executable("GroupNode", "GroupNode", params, results), next_executables, params, results)
        self.group_name = group_name
        self.group_task = group_task

    def execute(self, input_content):
        if not self.next_executables or len(self.next_executables) == 0:
            raise Exception("GroupNode do not have executables")
        group_threads = []
        for next_executable in self.next_executables:
            current_ctx = ctx.retrieves_all()
            group_thread = threading.Thread(
                target=lambda ne=next_executable, ic=input_content if not input_content else self.group_task: (
                    ctx.shared_context(current_ctx),
                    ne.execute(ic),
                    ctx.registers_global(ctx.retrieves([result["name"] for result in self.results]))
                )
            )
            group_threads.append(group_thread)
            group_thread.start()
        for group_thread in group_threads:
            group_thread.join()


class TaskNode(Node):
    def __init__(self, next_executables: [Executable], name, task, params, results):
        super().__init__(Executable("TaskNode", "TaskNode", params, results), next_executables, params, results)
        self.name = name
        self.task = task

    def execute(self, input_content):
        if not self.next_executables or len(self.next_executables) == 0:
            raise Exception("TaskNode do not have executables")
        task_threads = []
        for next_executable in self.next_executables:
            current_ctx = ctx.retrieves_all()
            task_thread = threading.Thread(
                target=lambda ne=next_executable, ic=input_content if not input_content else self.task: (
                    ctx.shared_context(current_ctx),
                    ne.execute(ic),
                    ctx.registers_global(ctx.retrieves([result["name"] for result in self.results]))
                )
            )
            task_threads.append(task_thread)
            task_thread.start()
        for task_thread in task_threads:
            task_thread.join()
