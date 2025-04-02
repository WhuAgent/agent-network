import traceback


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


def debug_function():
    stack = traceback.extract_stack()  # 获取当前调用栈
    for frame in stack:
        print(f"File {frame.filename}, line {frame.lineno}, in {frame.name}")
