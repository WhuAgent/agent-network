
class Route:
    def __init__(self):
        self.node_description = {}
        self.contact_list = dict()
        
        self.message_group_size = {}
        self.message_group = {}

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

    def register_contact(self, source, target, message_type, message_group_name=None):
        assert source in self.node_description, f"{source} does not exist!"
        assert target in self.node_description, f"{target} does not exist!"
        
        if message_group_name:
            if message_group_name not in self.message_group_size.keys():
                self.message_group_size[message_group_name] = 0
                self.message_group[message_group_name] = []
            
            self.message_group_size[message_group_name] += 1
            

        self.contact_list[source][target] = {"name": target, "message_type": message_type, "message_group": message_group_name}

    def deregister_contact(self, source, target):
        assert source in self.node_description, f"{source} does not exist!"
        assert target in self.node_description, f"{target} does not exist!"
        # TODO 上锁
        del self.contact_list[source][target]

    def check_contact(self, source, target):
        if target in self.contact_list[source].keys():
            return True, self.contact_list[source][target]["message_group"]
        else:
            return False, None

    def forward_message(self, source, target, message):
        if len(self.contact_list[source]) == 0 or target == "COMPLETE":
            return "COMPLETE", "COMPLETE"
        
        could_send, message_group_name = self.check_contact(source, target)

        assert could_send, f"{target} is not in {source}'s contact_list!"
        
        if isinstance(message, dict) and "message" in message:
            message = message["message"]
        
        if message_group_name:
            self.message_group[message_group_name].append(message)
            if len(self.message_group[message_group_name]) == self.message_group_size[message_group_name]:
                return target, self.message_group[message_group_name]
            else:
                return None, None
        else:
            return target, message if isinstance(message, list) else [message]

    def get_contactions(self, source):
        contactions = {}
        for item in self.contact_list[source]:
            target = item
            contactions.update({target: self.node_description[target]})
        return contactions
