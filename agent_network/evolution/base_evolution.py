from abc import abstractmethod
from agent_network.base import BaseAgent


class BaseEvolutionAgent(BaseAgent):

    def __init__(self, config, logger):
        # config = {
        #     "task": task,
        #     "name": name,
        #     "ref_id": name,
        #     "role": "",
        #     "description": description,
        #     "params": params,
        #     "results": results,
        #     "model": "",
        #     "prompts": prompts,
        #     "tools": []
        # }
        super().__init__(config, logger)
        self.config = config
        self.code = config["code"]

        # if "append_history_num" in self.config:
        #     self.append_history_num = self.config["append_history_num"]
        # if "keep_history_num" in self.config:
        #     self.keep_history_num = self.config["keep_history_num"]
        # self.runtime_revision_number = 0

    @abstractmethod
    def forward(self, messages, **kwargs):
        messages, results = exec(self.code, messages, kwargs)
        return messages, results
