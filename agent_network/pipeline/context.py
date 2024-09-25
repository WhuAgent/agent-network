import threading

thread_local_data = threading.local()
global_map = {}


def register_global(key, value):
    global_map[key] = value


def registers_global(params_map):
    for key, value in params_map.items():
        register_global(key, value)


def retrieve_global(key):
    if key in global_map:
        return global_map.get(key)
    else:
        raise Exception(f"global context do not contain key: {key}")


def retrieve_global_all():
    return global_map


def release_global():
    global_map.clear()


def init():
    if not hasattr(thread_local_data, 'context'):
        thread_local_data.context = {}


def register(key, value):
    init()
    thread_local_data.context[key] = value


def registers(params_map):
    for key, value in params_map.items():
        register(key, value)


def retrieve(key):
    init()
    if key in thread_local_data.context:
        return thread_local_data.context.get(key)
    else:
        raise Exception(f"context do not contain key: {key}")


def retrieves(keys):
    return {key: retrieve(key) for key in keys}


def retrieves_all():
    init()
    return thread_local_data.context


def release():
    if hasattr(thread_local_data, 'context'):
        thread_local_data.context.clear()


def shared_context(ctx):
    for key, value in ctx.items():
        register(key, value)
