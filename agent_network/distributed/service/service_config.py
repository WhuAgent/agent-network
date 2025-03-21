class VertexConfig:
    def __init__(self, name, description, params, results, ip, port):
        self.name = name
        self.description = description
        self.params = params
        self.results = results
        self.service_name = None
        self.service_group = None
        self.ip = ip
        self.port = port
