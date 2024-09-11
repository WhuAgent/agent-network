import threading

thread_local_data = threading.local()


def register(key, value):
    if not hasattr(thread_local_data, 'context'):
        thread_local_data.context = {}
    thread_local_data.context[key] = value


def retrieve(key):
    if hasattr(thread_local_data, 'context'):
        if key in thread_local_data.context:
            return thread_local_data.context.get(key)
        else:
            raise Exception(f"context do not contain key: {key}")
    else:
        raise Exception(f"context do not init")


def release():
    if hasattr(thread_local_data, 'context'):
        thread_local_data.context.clear()


def shared_context(self, ctx):
    for key, value in ctx:
        register(key, value)
