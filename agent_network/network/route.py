class Route:
    def __init__(self):
        self.node_description = {}
        self.contact_list = dict()
        self.hard_contact_list = dict()
        self.group_contact_list = dict()

    def node_exist(self, name):
        return name in self.node_description

    def register_node(self, name, description):
        assert name not in self.node_description, f"{name} already exists!"

        self.node_description[name] = description
        self.contact_list[name] = {}

    def deregister_node(self, name):
        assert name in self.node_description, f"{name} does not exist!"
        # TODO 上锁
        del self.contact_list[name]
        for source in list(self.contact_list.keys()):
            for target in list(self.contact_list[source].keys()):
                if target == name:
                    del self.contact_list[source][name]
        del self.node_description[name]

    def register_contact(self, group, source, target, message_type, rule):
        assert source in self.node_description, f"{source} does not exist!"
        assert target in self.node_description, f"{target} does not exist!"

        self.contact_list[source][target] = {}
        self.contact_list[source][target][rule] = {"name": target, "message_type": message_type}
        if "hard" == rule:
            self.hard_contact_list.setdefault(group, {})
            self.hard_contact_list[group].setdefault(source, {})
            self.hard_contact_list[group][source][target] = {"name": target, "message_type": message_type}

    def deregister_contact(self, source, target):
        assert source in self.node_description, f"{source} does not exist!"
        assert target in self.node_description, f"{target} does not exist!"
        # TODO 上锁
        if source in self.contact_list and target in self.contact_list[source]:
            del self.contact_list[source][target]
        for group in self.hard_contact_list:
            if source in self.hard_contact_list[group] and target in self.hard_contact_list[group][source]:
                del self.hard_contact_list[group][source][target]

    def check_contact(self, source, target):
        for item in self.contact_list[source]:
            if target == item:
                return True
        return False

    def forward_message(self, source, target, message):
        if len(self.contact_list[source]) == 0 or target == "COMPLETE":
            return "COMPLETE", "COMPLETE"

        assert self.check_contact(source, target), f"{target} is not in {source}'s contact_list!"

        if isinstance(message, dict) and "message" in message:
            message = message["message"]

        return target, message

    def forward(self, group, source, message):
        if isinstance(message, dict) and "message" in message:
            message = message["message"]

        if len(self.contact_list[source]) == 0:
            return [], message

        targets = []
        if group in self.hard_contact_list:
            if source in self.hard_contact_list[group]:
                targets.extend(list(self.hard_contact_list[group][source].keys()))

        return targets, message

    def get_contactions(self, source):
        contactions = {}
        for item in self.contact_list[source]:
            target = item
            contactions.update({target: self.node_description[target]})
        return contactions
