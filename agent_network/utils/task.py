from agent_network.network.vertexes.vertex import Vertex
from agent_network.network.vertexes.graph_vertex import GroupVertex, AgentVertex, ThirdPartyAgentVertex, ThirdPartyGroupVertex


def get_task_type(vertex: Vertex):
    if isinstance(vertex, AgentVertex) or isinstance(vertex, ThirdPartyAgentVertex):
        type = "agent"
    elif isinstance(vertex, GroupVertex) or isinstance(vertex, ThirdPartyGroupVertex):
        type = "group" if vertex.type == "agent" else vertex.type
    else:
        raise Exception(f"task type error: {vertex.name}")
    return type
