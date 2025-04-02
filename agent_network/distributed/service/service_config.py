class VertexConfig:
    def __init__(self, name, title, description, params, results, ip, port, type="agent"):
        self.name = name
        self.title = title
        self.description = description
        self.params = params
        self.results = results
        self.service_name = None
        self.service_group = None
        self.ip = ip
        self.port = port
        self.type = type
