import json

from agent_network.network.executable import Executable
import requests


class ThirdPartyExecutable(Executable):
    def __init__(self, name, task, description, service_group, service_name, ip, port):
        super().__init__(name, task, description)
        self.service_group = service_group
        self.service_name = service_name
        self.ip = ip
        self.port = port

    def execute(self, input_content, **kwargs):
        params = {"task": "123", "node": self.name}
        response = requests.post(f"http://{self.ip}:{self.port}/service", params=params, json=json.dumps(kwargs))
        return input_content, response.json(), []

    def release(self):
        pass
