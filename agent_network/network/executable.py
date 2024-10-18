from abc import abstractmethod


class Executable:
    def __init__(self, name, task):
        self.name = name
        self.task = task

    @abstractmethod
    def execute(self, input_content, **kwargs):
        pass


class ParameterizedExecutable(Executable):
    def __init__(self, name, task, params, results):
        super().__init__(name, task)
        self.params = params
        self.results = results

    @abstractmethod
    def execute(self, input_content, **kwargs):
        pass
