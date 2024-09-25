from abc import abstractmethod


class Executable:
    def __init__(self, name, task, params, results):
        self.name = name
        self.task = task
        self.params = params
        self.results = results

    @abstractmethod
    def execute(self, input_content):
        pass
