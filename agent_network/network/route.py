
class Route:
    def __init__(self):
        self.node_description = {}
        self.contact_list = dict()

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
        for source in self.contact_list:
            for target in self.contact_list[source]:
                if target == name:
                    del self.contact_list[source][name]

    def register_contact(self, source, target, message_type):
        assert source in self.node_description, f"{source} does not exist!"
        assert target in self.node_description, f"{target} does not exist!"

        self.contact_list[source][target] = {"name": target, "message_type": message_type}

    def deregister_contact(self, source, target):
        assert source in self.node_description, f"{source} does not exist!"
        assert target in self.node_description, f"{target} does not exist!"
        # TODO 上锁
        del self.contact_list[source][target]

    def check_contact(self, source, target):
        for item in self.contact_list[source]:
            if target == item:
                return True
        return False

    def forward_message(self, source, target, message):
        if len(self.contact_list[source]) == 0:
            return "COMPLETE", "COMPLETE"

        assert self.check_contact(source, target), f"{target} is not in {source}'s contact_list!"

        if isinstance(message, dict) and "message" in message:
            message = message["message"]

        return target, message

    def get_contactions(self, source):
        contactions = {}
        for item in self.contact_list[source]:
            target = item
            contactions.update({target: self.node_description[target]})
        return contactions
