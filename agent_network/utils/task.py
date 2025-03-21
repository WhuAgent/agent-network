from agent_network.network.vertexes.vertex import Vertex
from agent_network.network.vertexes.graph_vertex import GroupVertex, AgentVertex


def get_task_type(vertex: Vertex):
    if isinstance(vertex, AgentVertex):
        type = "agent"
    elif isinstance(vertex, GroupVertex):
        type = "group"
    else:
        # todo 如何判断tbot类型
        type = "tbot"
    return type
