from agent_network.base import BaseAgent


class Agent1(BaseAgent):
    def __init__(self, graph, config, logger):
        super().__init__(graph, config, logger)

    def forward(self, message, **kwargs):
        messages = []
        self.add_message("user", f"number1: {kwargs['number1']} number2: {kwargs['number2']}", messages)
        response = self.chat_llm(messages)
        print('response: ' + response.content)
        result = int(kwargs['number1']) + int(kwargs['number2'])
        results = {
            "bool_result": '1',
            "result": result,
        }
        return messages, results


class Agent2(BaseAgent):
    def __init__(self, graph, config, logger):
        super().__init__(graph, config, logger)

    def forward(self, message, **kwargs):
        messages = []
        # self.add_message("user", f"number1: {kwargs['number1']} number2: {kwargs['number2']}", messages)
        # response = self.chat_llm(messages)
        # print('response: ' + response.content)
        result = int(kwargs['number1']) + int(kwargs['number2'])
        results = {
            "bool_result": '1',
            "result": result,
        }
        return messages, results
