from agent_network.base import BaseAgent
import yaml


class EvolutionNewAgent(BaseAgent):
    def __init__(self, config, logger):
        super().__init__(config, logger)

    def forward(self, message, **kwargs):
        task = kwargs['task']
        messages = []
        template_config_path = 'config/System/AgentTemplate.yaml'
        with open(template_config_path, "r", encoding="UTF-8") as f:
            template = yaml.safe_load(f)
        self.add_message("user", f"task: {task}", messages)
        self.add_message("user", f"template: {template}", messages)
        response = self.chat_llm(messages)
        results = {
            "config": response.content,
        }
        return messages, results
