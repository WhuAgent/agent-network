from agent_network.network.executable import Executable
import requests


class ThirdPartyExecutable(Executable):
    def __init__(self, id, description, service_group, service_name, ip, port):
        super().__init__(id, description)
        self.service_group = service_group
        self.service_name = service_name
        self.ip = ip
        self.port = port

    def execute(self, input_content, **kwargs):
        params = {"task": kwargs["task"] if "task" in kwargs else None, "vertex": self.id}
        # TODO 参数为None
        response = requests.post(f"http://{self.ip}:{self.port}/service", params=params, json=kwargs)
        if response.status_code != 200:
            raise Exception(
                f"Third party vertex: {self.id} from service: {self.service_name}&&{self.service_group} with instance [{self.ip}:{self.port}] is not available")
        return input_content, response.json()

    def release(self):
        pass
