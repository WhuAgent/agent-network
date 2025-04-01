import threading

from agent_network.utils.llm.message import Message

thread_local_data = threading.local()
global_map = {}
graph_key = "$$$$$Graph$$$$$"
graph_id_key = "$$$$$GraphID$$$$$"
task_id_key = "$$$$$TaskID$$$$$"
sub_task_id_key = "$$$$$SubTaskID$$$$$"


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
    if not params_map:
        return
    for key, value in params_map.items():
        register(key, value)


def registers_params(params_list):
    if params_list is None:
        return
    for param in params_list:
        register(param['name'], param['value'])


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


def register_graph(id, graph):
    if retrieve(graph_key) is not None or retrieve(graph_id_key) is not None:
        raise Exception("graph register duplicated")
    register(graph_key, graph)
    register(graph_id_key, id)


def retrieve_graph():
    graph = retrieve(graph_key)
    if graph is None:
        raise Exception("graph is not within current context")
    return graph


def retrieve_graph_id():
    graph_id = retrieve(graph_id_key)
    if graph_id is None:
        raise Exception("graph id is not within current context")
    return graph_id


def register_time(time_cost):
    graph = retrieve(graph_key)
    if graph is None:
        raise Exception("graph is not in the current context")

    graph.cur_execution.time_cost = time_cost

    graph.total_time += time_cost

    graph.logger.log("network", f"AGENT {graph.cur_execution.cur_executor.id} time cost: {time_cost}", "Agent-Network")


def register_llm_action(messages: list[Message]):
    graph = retrieve(graph_key)
    if graph is None:
        raise Exception("graph is not in the current context")
    vertex = graph.cur_execution.cur_executor.executable.name

    for i in range(len(graph.vertex_messages[vertex]), len(messages)):
        graph.vertex_messages[vertex].append(messages[i])

    for i in range(graph.message_num, len(messages)):
        graph.cur_execution.llm_messages.append(messages[i])
        graph.message_num += 1


def register_task_id(task_id, subtask_id):
    if retrieve(task_id_key) is not None or retrieve(sub_task_id_key) is not None:
        raise Exception("task register duplicated")
    register(task_id_key, task_id)
    register(sub_task_id_key, subtask_id)


def retrieve_task_id():
    task_id = retrieve(task_id_key)
    subtask_id = retrieve(sub_task_id_key)
    if task_id is None or subtask_id is None:
        raise Exception("task id is not within current context")
    return task_id, subtask_id
