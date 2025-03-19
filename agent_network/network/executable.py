from abc import abstractmethod
from datetime import datetime


class Executable:
    def __init__(self, id, description):
        self.id = id
        self.description = description
        self.create_time = datetime.now().timestamp()

    @abstractmethod
    def execute(self, input_content, **kwargs):
        pass

    @abstractmethod
    def release(self):
        pass


class ParameterizedExecutable(Executable):
    def __init__(self, id, description, params, results):
        super().__init__(id, description)
        self.params = params or {}
        self.results = results or {}
        self.description = description

    @abstractmethod
    def execute(self, input_content, **kwargs):
        pass

    @abstractmethod
    def release(self):
        pass
