from agent_network.network.executable import Executable
import agent_network.pipeline.context as ctx
from agent_network.network.nodes.node import Node


class GroupNode(Node):
    def __init__(self, executable: Executable, group_name, group_task, params, results):
        super().__init__(Executable(group_name, group_task), params, results)
        self.group_name = group_name
        self.group_task = group_task
        self.executable = executable

    def execute(self, input_content, **kwargs):
        combined_params = {**kwargs, **ctx.retrieves([param["name"] for param in self.params])}
        self.executable.execute(input_content, **combined_params)
        ctx.registers_global(ctx.retrieves([result["name"] for result in self.results]))
        # group_threads = []
        # for next_executable in self.next_executables:
        #     current_ctx = ctx.retrieves_all()
        #     group_thread = threading.Thread(
        #         target=lambda ne=next_executable, ic=input_content if not input_content else self.group_task: (
        #             ctx.shared_context(current_ctx),
        #             ne.execute(ic),
        #             ctx.registers_global(ctx.retrieves([result["name"] for result in self.results]))
        #         )
        #     )
        #     group_threads.append(group_thread)
        #     group_thread.start()
        # for group_thread in group_threads:
        #     group_thread.join()
