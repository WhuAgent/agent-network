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
        params = {"task": kwargs["task"] if "task" in kwargs else None, "node": self.name}
        # TODO 参数为None
        response = requests.post(f"http://{self.ip}:{self.port}/service", params=params, json=kwargs)
        if response.status_code != 200:
            raise Exception(
                f"Third party node: {self.name} from service: {self.service_name}&&{self.service_group} with instance [{self.ip}:{self.port}] is not available")
        return input_content, response.json()

    def release(self):
        pass
