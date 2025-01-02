import threading

from agent_network.utils.llm.message import Message

thread_local_data = threading.local()
global_map = {}
pipeline_key = "$$$$$Pipeline$$$$$"
pipeline_id_key = "$$$$$PipelineID$$$$$"


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


def retrieves_global(keys):
    return {key: retrieve_global(key) for key in keys}


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
    if params_map is None:
        return
    for key, value in params_map.items():
        register(key, value)


def retrieve(key):
    init()
    return thread_local_data.context.get(key)


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


def delete(key):
    thread_local_data.context.pop(key)


def register_pipeline(id, pipeline):
    if retrieve(pipeline_key) is not None or retrieve(pipeline_id_key) is not None:
        raise Exception("pipeline register duplicated")
    register(pipeline_key, pipeline)
    register(pipeline_id_key, id)


def retrieve_pipline():
    pipeline = retrieve(pipeline_key)
    if pipeline is None:
        raise Exception("pipeline is not within current context")
    return pipeline


def retrieve_pipline_id():
    pipeline_id = retrieve(pipeline_id_key)
    if pipeline_id is None:
        raise Exception("pipeline id is not within current context")
    return pipeline_id


def register_time(time_cost):
    pipeline = retrieve(pipeline_key)
    if pipeline is None:
        raise Exception("pipeline is not in the current context")

    pipeline.cur_execution.time_cost = time_cost

    pipeline.total_time += time_cost

    pipeline.logger.log("network", f"AGENT {pipeline.cur_execution.cur_executor.name} time cost: {time_cost}", "Agent-Network")


def register_llm_action(messages: list[Message]):
    pipeline = retrieve(pipeline_key)
    if pipeline is None:
        raise Exception("pipeline is not in the current context")
    node = pipeline.cur_execution.cur_executor.name

    for i in range(len(pipeline.node_messages[node]), len(messages)):
        pipeline.node_messages[node].append(messages[i])
    
    for i in range(pipeline.message_num, len(messages)):
        pipeline.cur_execution.llm_messages.append(messages[i])
        pipeline.message_num += 1