from agent_network.network.executable import Executable
import requests


class ThirdPartyExecutable(Executable):
    def __init__(self, id, title, description, service_group, service_name, ip, port, type="agent"):
        super().__init__(id, description)
        self.name = id
        self.service_group = service_group
        self.service_name = service_name
        self.title = title
        self.ip = ip
        self.port = port
        self.type = type

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


# todo 从注册中心上同步这个调度服务
class ThirdPartySchedulerExecutable(Executable):
    def __init__(self, subtask_id, task_id, graph, organizeId, level_routes):
        super().__init__(task_id, "调度服务")
        self.graph = graph
        self.level_routes = level_routes
        self.url = "http://120.27.248.186:10696/api/engine/flow"
        self.organizeId = organizeId
        self.subtask_id = subtask_id

    def execute(self, **kwargs):
        data = {
            "flowId": "@cn.com.thingo.intelligentAgentPlatform.taskScheduling/FLOW_SCHEDULE_BASED_ON_TASK_ID",
            "params": {
                "taskId": self.id,
                "levelRoutes": self.level_routes,
                "organizeId": self.organizeId,
                "executionGraph": repr(self.graph.trace)
            }
        }
        response = requests.post(self.url, json=data)
        if response.status_code != 200:
            raise Exception(
                f"Third party Scheduler: {self.url} is not available")
        return None, response.json()

    def synchronize(self, subtaskStatus):
        data = {
            "flowId": "@cn.com.thingo.intelligentAgentPlatform.taskScheduling/FLOW_SYNCHRONIZE_TASK_EXECUTION_GRAPH",
            "params": {
                "taskId": self.id,
                "organizeId": self.organizeId,
                "executionGraph": repr(self.graph.trace),
                "subtaskId": self.subtask_id,
                "subtaskStatus": subtaskStatus.value
            }
        }
        response = requests.post(self.url, json=data)
        if response.status_code != 200:
            raise Exception(
                f"Third party Scheduler synchronize failed: {self.url}")
        return None, response.json()

    def summary(self, agent_network_summarize_reasoning, agent_network_final_result):
        data = {
            "flowId": "@cn.com.thingo.intelligentAgentPlatform.taskScheduling/FLOW_SUMMARY_OF_RECEIVING_TASKS",
            "params": {
                "taskId": self.id,
                "subtaskId": self.subtask_id,
                "taskSummary": {
                    "agentNetworkSummarizeReasoning": agent_network_summarize_reasoning,
                    "agentNetworkFinalResult": agent_network_final_result
                },
            }
        }
        response = requests.post(self.url, json=data)
        if response.status_code != 200:
            raise Exception(
                f"Third party Scheduler summary failed: {self.url}")
        return None, response.json()

    def release(self):
        pass
