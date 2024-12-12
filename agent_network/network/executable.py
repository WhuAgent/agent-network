from abc import abstractmethod


class Executable:
    # todo delete task
    def __init__(self, name, task, description):
        self.name = name
        self.task = task
        self.description = description

        self.cur_execution_cost = {
            "time": 0,
            "llm_usage_history": []
        }

    @abstractmethod
    def execute(self, input_content, **kwargs):
        pass

    @abstractmethod
    def release(self):
        pass

class ParameterizedExecutable(Executable):
    def __init__(self, name, task, description, params, results):
        super().__init__(name, task, description)
        self.params = params
        self.results = results
        self.description = description

    @abstractmethod
    def execute(self, input_content, **kwargs):
        pass

    @abstractmethod
    def release(self):
        pass
