from abc import abstractmethod


class Executable:
    def __init__(self, name, task):
        self.name = name
        self.task = task

    @abstractmethod
    def execute(self, input_content):
        pass
