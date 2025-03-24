from agent_network.communication.communicate import Communicate
from agent_network.utils.llm.message import SystemMessage, UserMessage
from agent_network.utils.llm.chat import chat_llm_json

import agent_network.graph.context as ctx


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
        assert name not in self.vertex_description, f"{name} already exists!"

        self.vertex_description[name] = description
        self.vertex_params[name] = params
        self.vertex_results[name] = results
        self.contact_list[name] = {}

    def deregister_vertex(self, name):
        assert name in self.vertex_description, f"{name} does not exist!"
        # TODO 上锁
        del self.contact_list[name]
        for source in list(self.contact_list.keys()):
            for target in list(self.contact_list[source].keys()):
                if target == name:
                    del self.contact_list[source][name]
        del self.vertex_description[name]

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

    def forward_message(self, source, target):
        if len(self.contact_list[source]) == 0 or target == "COMPLETE":
            return "COMPLETE"

        assert self.check_contact(source, target), f"{target} is not in {source}'s contact_list!"

        current_context = ctx.retrieves_all()
        current_step = ctx.retrieve("step")
        ignored_context = ["$$$$$Graph$$$$$", "$$$$$GraphID$$$$$", "sub_tasks", "step"]
        valuable_context = {}
        for key, value in current_context.items():
            if key not in ignored_context:
                valuable_context[key] = value

        related_context = self.get_related_context(source, target, valuable_context, current_step)
        if len(related_context) != len(self.vertex_params[target]):
            matched_context = self.match_context(valuable_context, target)
            ctx.registers(matched_context)

        return target

    def forward_start(self, target):
        current_context = ctx.retrieves_all()
        current_step = ctx.retrieve("step")
        ignored_context = ["$$$$$Graph$$$$$", "$$$$$GraphID$$$$$", "sub_tasks", "step"]
        valuable_context = {}
        for key, value in current_context.items():
            if key not in ignored_context:
                valuable_context[key] = value

        related_context = self.get_related_context("start", target, valuable_context, current_step)
        if len(related_context) != len(self.vertex_params[target]):
            matched_context = self.match_context(valuable_context, target)
            ctx.registers(matched_context)

    def get_related_context(self, source, target, current_context, current_step):
        related_context = {}
        for param in self.vertex_params[target]:
            param_name = param.get("name")
            if current_context.get(param_name) is not None:
                related_context[param_name] = current_context[param_name]
        return related_context

    def match_context(self, context, target):
        messages = [
            SystemMessage(
                "### 角色 ###\n你是一个出色的服务协调者，在服务系统中，当上游服务的结果与下游服务所需的参数对不上时，你能够灵活地转换上游服务写入到上下文中的信息，从而实现服务间的联动。\n\n### 目标 ###\n给定上下文信息，和下游服务所需的参数，你需要补全上下文中缺失的参数，以让下游服务能够正确获取其所需信息。\n\n### 工作流 ###\n1. 首先理解上下文中已有的参数和下游服务所需的参数。\n2. 找到下游服务所需参数中，上下文不包含的参数。\n3. 在现有上下文中，寻找参数作用语义相似的参数，将其参数值作为下游服务所需参数的参数值。\n4. 将所有的缺失参数与对应参数值返回。\n\n\n### 返回方式 ###\n请以 JSON 方式返回一个参数字典，键为对应参数名，值为对应的参数值。\n\n### 返回示例 ###\n{\n    \"arg1_name\": \"arg1_value\",\n    \"arg2_name\": \"arg2_value\",\n    \"...\": \"...\"\n}\n"),
            UserMessage(
                f"现在，上下文中的信息如下：\n{context}\n\n而下游服务所需要的参数为：\n{self.vertex_params[target]}\n\n请为上下文增添新的参数，以让下游服务正确获取到其所需信息。")
        ]

        response = chat_llm_json(messages)

        return response.content

    def search(self, source):
        targets = None

        # if self.all_results_generated(ctx.retrieves_all(), final_results):
        #     targets = ["COMPLETE"]

        # 寻找硬路由
        if not targets:
            targets = self.find_hard_targets(source)

        if not targets and source in self.contact_list:
            targets_map = self.contact_list[source]
            target_avaliable = targets_map.keys()
            current_step = ctx.retrieve("step")
            sub_tasks = ctx.retrieve("sub_tasks")
            if current_step is not None and sub_tasks is not None:
                targets = [0] if current_step == -1 else sub_tasks[current_step]["next"]
                for i, target in enumerate(targets):
                    targets[i] = sub_tasks[target].get("executor") if target != -1 else "COMPLETE"

                for target in targets:
                    if target != "COMPLETE" and target not in target_avaliable:
                        self.register_contact(source, target, "soft")
        return targets if targets is not None else []

    def all_results_generated(self, current_context, final_results):
        if final_results is None:
            return True
        for item in final_results:
            if current_context.get(item) is None:
                return False
        return True

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
