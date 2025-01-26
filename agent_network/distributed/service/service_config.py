class NodeConfig:
    def __init__(self, name, description, task, params, results, ip, port):
        self.name = name
        self.description = description
        self.task = task
        self.params = params
        self.results = results
        self.service_name = None
        self.service_group = None
        self.ip = ip
        self.port = port
