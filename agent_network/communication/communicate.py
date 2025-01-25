from abc import abstractmethod


class Communicate:
    @abstractmethod
    def search(self, **kwargs):
        pass
