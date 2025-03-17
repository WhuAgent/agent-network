from agent_network.utils.llm.message import Message
import _thread

global_map = {}
global_thread_map = {}
graph_key = "$$$$$Graph$$$$$"
graph_id_key = "$$$$$GraphID$$$$$"


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
    id = _thread.get_ident()
    if id not in global_thread_map:
        global_thread_map[id] = {}


def register(key, value):
    id = _thread.get_ident()
    init()
    global_thread_map[id][key] = value


def registers(params_map):
    if params_map is None:
        return
    for key, value in params_map.items():
        register(key, value)


def retrieve(key):
    id = _thread.get_ident()
    return global_thread_map[id].get(key)


def retrieves(keys):
    return {key: retrieve(key) for key in keys}


def retrieves_all():
    init()
    id = _thread.get_ident()
    return global_thread_map[id]


def release():
    id = _thread.get_ident()
    if id in global_thread_map:
        global_thread_map[id].clear()


def shared_context(ctx):
    for key, value in ctx.items():
        register(key, value)


def delete(key):
    id = _thread.get_ident()
    global_thread_map[id].pop(key)


def register_graph(id, graph):
    init()
    id = _thread.get_ident()
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
    vertex = graph.cur_execution.cur_executor.id

    for i in range(len(graph.vertex_messages[vertex]), len(messages)):
        graph.vertex_messages[vertex].append(messages[i])
    
    for i in range(graph.message_num, len(messages)):
        graph.cur_execution.llm_messages.append(messages[i])
        graph.message_num += 1