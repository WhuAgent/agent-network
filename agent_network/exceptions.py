class RetryError(Exception):
    """
    RetryError
    """
    def __init__(self, message):
        self.message = message


class ReportError(Exception):
    """
    ReportError
    """
    def __init__(self, error_message, next_vertex):
        self.error_message = error_message
        self.next_vertex = next_vertex
        self.message = error_message
