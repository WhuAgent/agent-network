from abc import abstractmethod


class Executable:
    def __init__(self, name, task, description):
        self.name = name
        self.task = task
        self.description = description

    @abstractmethod
    def execute(self, input_content, **kwargs):
        pass

    def add_message(self, role, content):
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
