class Parameter:
    def __init__(self, title, name, description, value, type):
        self.title = title
        self.name = name
        self.description = description
        self.value = value
        self.type = type

    def __repr__(self):
        repr_map = {
            "title": self.title,
            "name": self.name,
            "description": self.description,
            "value": self.value,
            "type": self.type
        }
        return f"{repr_map}"
