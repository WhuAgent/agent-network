from agent_network.communication.communicate import Communicate
from agent_network.task.task_call import TaskStatus
from agent_network.utils.llm.message import SystemMessage, UserMessage
from agent_network.utils.llm.chat import chat_llm_json

import agent_network.graph.context as ctx

from agent_network.task.vertex import TaskVertex
from agent_network.task.manager import TaskManager

from agent_network.utils.llm.message import SystemMessage, UserMessage
from agent_network.utils.llm.chat import chat_llm_json


class Route(Communicate):
    def __init__(self):
        self.vertex_description = {}
        self.vertex_params = {}
        self.vertex_results = {}
        self.contact_list = dict()
        self.hard_contact_list = dict()
        self.group_contact_list = dict()

    def vertex_exist(self, name):
        return name in self.vertex_description

    def register_vertex(self, name, description, params, results):
        if name not in self.vertex_description:
            self.vertex_description[name] = description
            self.vertex_params[name] = params
            self.vertex_results[name] = results
            self.contact_list[name] = {}

    def deregister_vertex(self, name):
        if name in self.vertex_description:
            del self.contact_list[name]
            for source in list(self.contact_list.keys()):
                for target in list(self.contact_list[source].keys()):
                    if target == name:
                        del self.contact_list[source][name]
            del self.vertex_description[name]
            del self.vertex_params[name]
            del self.vertex_results[name]

    def register_contact(self, source, target, rule):
        assert source in self.vertex_description, f"{source} does not exist!"
        assert target in self.vertex_description, f"{target} does not exist!"

        self.contact_list[source][target] = {}
        self.contact_list[source][target][rule] = {"name": target}
        if "hard" == rule:
            self.hard_contact_list.setdefault(source, {})
            self.hard_contact_list[source][target] = {"name": target}

    def deregister_contact(self, source, target):
        assert source in self.vertex_description, f"{source} does not exist!"
        assert target in self.vertex_description, f"{target} does not exist!"
        # TODO 上锁
        if source in self.contact_list and target in self.contact_list[source]:
            del self.contact_list[source][target]
        if source in self.hard_contact_list and target in self.hard_contact_list[source]:
            del self.hard_contact_list[source][target]

    def check_contact(self, source, target):
        for item in self.contact_list[source]:
            if target == item:
                return True
        return False

    def forward_message(self, source, next_task):
        target = next_task.get("executor")

        if len(self.contact_list[source]) == 0 or target == "COMPLETE":
            return "COMPLETE"

        assert self.check_contact(source, target), f"{target} is not in {source}'s contact_list!"

        # current_context = ctx.retrieves_all()
        # current_step = ctx.retrieve("step")
        # ignored_context = ["$$$$$Graph$$$$$", "$$$$$GraphID$$$$$", "sub_tasks", "step"]
        # valuable_context = {}
        # for key, value in current_context.items():
        #     if key not in ignored_context:
        #         valuable_context[key] = value

        # related_context = self.get_related_context(source, target, valuable_context, current_step)
        # if len(related_context) != len(self.vertex_params[target]):
        #     matched_context = self._match_context(valuable_context, target)
        #     ctx.registers(matched_context)

        return target

    # def forward_start(self, target):
    #     current_context = ctx.retrieves_all()
    #     ignored_context = ["$$$$$Graph$$$$$", "$$$$$GraphID$$$$$", "sub_tasks", "step"]
    #     valuable_context = {}
    #     for key, value in current_context.items():
    #         if key not in ignored_context:
    #             valuable_context[key] = value

    #     related_context = self.get_related_context(target, valuable_context)
    #     if len(related_context) != len(self.vertex_params[target]):
    #         matched_context = self._match_context(valuable_context, target)
    #         ctx.registers(matched_context)

    def match_context(self, target):
        valuable_context = self.get_valuable_context()

        related_context = self.get_related_context(target, valuable_context)
        if len(related_context) != len(self.vertex_params[target]):
            matched_context = self._match_context(valuable_context, target)
            ctx.registers(matched_context)
            
    def get_valuable_context(self, ignored_context=[]):
        current_context = ctx.retrieves_all()
        final_ignored_context = ["$$$$$Graph$$$$$", "$$$$$GraphID$$$$$", "sub_tasks", "step"]
        final_ignored_context.extend(ignored_context)
        valuable_context = {}
        for key, value in current_context.items():
            if key not in final_ignored_context:
                valuable_context[key] = value
        
        return valuable_context

    def get_related_context(self, target, current_context):
        related_context = {}
        for param in self.vertex_params[target]:
            param_name = param.get("name")
            if current_context.get(param_name) is not None:
                related_context[param_name] = current_context[param_name]
        return related_context

    def _match_context(self, context, target):
        messages = [
            SystemMessage(
                "### 角色 ###\n你是一个出色的服务协调者，在服务系统中，当上游服务的结果与下游服务所需的参数对不上时，你能够灵活地转换上游服务写入到上下文中的信息，从而实现服务间的联动。\n\n### 目标 ###\n给定上下文信息，和下游服务所需的参数，你需要补全上下文中缺失的参数，以让下游服务能够正确获取其所需信息。\n\n### 工作流 ###\n1. 首先理解上下文中已有的参数和下游服务所需的参数。\n2. 找到下游服务所需参数中，上下文不包含的参数。\n3. 在现有上下文中，寻找参数作用语义相似的参数，将其参数值作为下游服务所需参数的参数值。\n4. 将所有的缺失参数与对应参数值返回。\n\n\n### 返回方式 ###\n请以 JSON 方式返回一个参数字典，键为对应参数名，值为对应的参数值。\n\n### 返回示例 ###\n{\n    \"arg1_name\": \"arg1_value\",\n    \"arg2_name\": \"arg2_value\",\n    \"...\": \"...\"\n}\n"),
            UserMessage(
                f"现在，上下文中的信息如下：\n{context}\n\n而下游服务所需要的参数为：\n{self.vertex_params[target]}\n\n请为上下文增添新的参数，以让下游服务正确获取到其所需信息。")
        ]

        response = chat_llm_json(messages)

        return response.content

    def search(self, cur_task: TaskVertex, task_manager: TaskManager, execution_graph, user_task, vertexes_description):
        next_tasks = None

        # 当前任务信息
        task = cur_task.get_task()
        executor = cur_task.executable.name
        
        # 获取历史任务信息
        history_task_info = []
        for task in task_manager.task_queue.values():
            if task.status == TaskStatus.SUCCESS:
                history_task_info.append({
                    "task": task.task,
                    "executor": task.executable.name
                })
                
        # 获取上下文信息
        valuable_context = self.get_valuable_context()
        
        # 判断任务是否完成
        if self.user_task_complete(user_task, history_task_info, valuable_context):
            return []

        # 寻找硬路由
        if not next_tasks:
            if targets := self.find_hard_targets(executor):
                next_tasks = [
                    {
                        "id": None,
                        "task": task,
                        "executor": target,
                    } for target in targets
                ]

        # 按照 task_manager 走下一个 task
        if not next_tasks:
            next_tasks = [
                {
                    "id": id,
                    "task": task_manager.get_task(id).get_task(),
                    "executor": task_manager.get_task(id).executable.name
                } for id in cur_task.next
            ]

        # 基于软路由的规划
        next_tasks = self.plan_based_soft_route(executor, vertexes_description, user_task, history_task_info, valuable_context, next_tasks)
        
        return next_tasks if next_tasks is not None else []

    def user_task_complete(self, user_task, history_task_info, current_context):
        messages = [
            SystemMessage("你是一个专业的任务进程管理者，擅长判断任务是否已经完成。现在给定用户需求、历史执行任务和当前执行上下文，判断任务是否已经完成。请以 json 形式返回，包括一个字段 complete，值为 true 或 false。"),
            UserMessage(f"现在用户的需求为{user_task}, 历史执行任务为{history_task_info}，当前执行上下文为{current_context}")
        ]
        
        resposne = chat_llm_json(messages)
        
        if resposne.content["complete"]:
            return True
        else:
            return False
    
    def plan_based_soft_route(self, executor, vertexes_description, user_task, history_task_info, valuable_context, next_tasks):
        agent_description = {}
        for target in self.contact_list[executor].values():
            if "soft" in target:
                agent_description[target["soft"]["name"]] = vertexes_description[target["soft"]["name"]]
        
        # 只有当当前智能体有软路由时，才针对软路由进行规划
        if len(agent_description) > 0:
            messages = [
                SystemMessage(f"### 角色 ###\n你是一个专业的任务规划者，善于根据用户需求和当前执行情况，精确计划下一步任务。\n\n### 目标 ###\n现在给定用户需求、当前执行图和预期进行的下一步任务，你需要判断现有信息能否支持下一步任务的进行，决策出最终的下一步任务。\n\n### 工作流 ###\n你需要按照如下工作流进行工作：\n\n1. 理解用户需求和当前的执行图，判断任务进行的进程；\n2. 理解预期进行的下一步任务，判断当前执行过程和上下文信息是否足以让任务进行到预期的下一步。\n3. 如果可以按照预期进行下一步任务，请直接返回预期的下一步任务；\n4. 如果为了更好地完成下一步任务，需要进行其他任务以补充信息，请从当前智能体的协作智能体中挑选一个智能体，并为其分配下一步任务。\n\n### 可选智能体 ###\n {agent_description}\n\n### 返回格式 ###\n以 json 形式返回一个字典的列表，每个字典包含三项：\n\nid：如果是返回原来的任务，则 id 保持与输入相同，否则将 id 置为 None\ntask：规划的任务\nexecutor：执行任务的智能体\n\n### 示例返回 ###\n[\n  {{\n    \"id\": \"...\" \n    \"task\": \"...\",\n    \"executor\": \"...\"\n  }}\n  {{\n  \"...\"\n  }}\n  ]\n"),
                UserMessage(f"现在用户的需求是{user_task}, 在执行用户需求时，历史执行任务为{history_task_info}，当前执行上下文为{valuable_context}，根据用户需求、历史执行任务和当前执行上下文信息，是否可以直接执行预期的下一步任务{next_tasks}？如果不行，请重新对下一步任务进行规划")
            ]
            
            response = chat_llm_json(messages)
            
            next_tasks = response.content
            
            if not isinstance(next_tasks, list):
                next_tasks = [next_tasks]
        
        return next_tasks

    def find_hard_targets(self, source):
        if len(self.contact_list[source]) == 0:
            return None

        targets = []
        if source in self.hard_contact_list:
            targets.extend(list(self.hard_contact_list[source].keys()))

        return targets if targets else None

    def get_contactions(self, source):
        contactions = {}
        for item in self.contact_list[source]:
            target = item
            contactions.update({target: self.vertex_description[target]})
        return contactions
