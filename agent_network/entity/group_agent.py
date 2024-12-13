from datetime import datetime


class GroupAgent:
    def __init__(self, begin_timestamp, name):
        self.begin_timestamp = begin_timestamp
        self.end_timestamp = begin_timestamp
        self.name = name

    def separate(self):
        self.end_timestamp = datetime.now().timestamp()
