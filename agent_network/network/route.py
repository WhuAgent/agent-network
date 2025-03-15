from agent_network.communication.communicate import Communicate


class Route(Communicate):
    def __init__(self):
        self.vertex_description = {}
        self.contact_list = dict()
        self.hard_contact_list = dict()
        self.group_contact_list = dict()

    def vertex_exist(self, name):
        return name in self.vertex_description

    def register_vertex(self, name, description):
        assert name not in self.vertex_description, f"{name} already exists!"

        self.vertex_description[name] = description
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

        return target

    def forward(self, source):
        if len(self.contact_list[source]) == 0:
            return []

        targets = []
        if source in self.hard_contact_list:
            targets.extend(list(self.hard_contact_list[source].keys()))

        return targets
    
    def all_results_generated(self, current_context, final_results):
        for item in final_results:
            if current_context.get(item) is None:
                return False
        return True

    def search(self, source, current_context, final_results):
        if self.all_results_generated(current_context, final_results):
            return ["COMPLETE"]
        targets = self.forward(source)
        if len(targets) > 0:
            return targets
        
        if source in self.contact_list:
            targets_map = self.contact_list[source]
            targets = targets_map.keys()
            # todo 用算法从软路由里找一些需要交流的
            return []
    def execute(self, group, source, target):
        pass

    def get_contactions(self, source):
        contactions = {}
        for item in self.contact_list[source]:
            target = item
            contactions.update({target: self.vertex_description[target]})
        return contactions
