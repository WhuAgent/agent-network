import time


class Executable:
    def __init__(self, id, description):
        self.id = id
        self.description = description
        self.create_time = time.time()

    def execute(self, input_content, **kwargs):
        pass

    def release(self):
        pass


class ParameterizedExecutable(Executable):
    def __init__(self, id, description, params, results):
        super().__init__(id, description)
        self.params = params
        self.results = results
        self.description = description

    def execute(self, input_content, **kwargs):
        pass

    def release(self):
        pass
