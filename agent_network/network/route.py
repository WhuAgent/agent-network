class Route:
    def __init__(self):
        self.node_description = {}
        self.contact_list = dict()

    def register_node(self, name, description):
        assert name not in self.node_description, f"{name} already exists!"

        self.node_description[name] = description
        self.contact_list[name] = []

    def register_contact(self, source, target, message_type):
        assert source in self.node_description, f"{source} does not exist!"
        assert target in self.node_description, f"{target} does not exist!"

        self.contact_list[source].append({"name": target, "message_type": message_type})

    def check_contact(self, source, target):
        for item in self.contact_list[source]:
            if target == item["name"]:
                return True
        return False

    def forward_message(self, source, target, message):
        if len(self.contact_list[source]) == 0:
            return "COMPLETE", "COMPLETE"

        assert self.check_contact(source, target), f"{target} is not in {source}'s contact_list!"

        return target, message

    def get_contactions(self, source):
        contactions = {}
        for item in self.contact_list[source]:
            target = item["name"]
            contactions.update({target: self.node_description[target]})
        return contactions
