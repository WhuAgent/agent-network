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
    def __init__(self, error_message, next_node):
        self.error_message = error_message
        self.next_node = next_node 
        self.message = error_message
