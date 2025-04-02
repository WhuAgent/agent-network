import json
import time
from abc import abstractmethod
from agent_network.network.network import Network
from agent_network.distributed.service.service_config import VertexConfig
from agent_network.network.vertexes.graph_vertex import AgentVertex, GroupVertex, ThirdPartyAgentVertex, \
    ThirdPartyGroupVertex
from agent_network.network.vertexes.third_party.executable import ThirdPartyExecutable
import threading


class Client:
    def __init__(self, network: Network, service_group, service_name, access_key, secret_key, center_addr, ip, port):
        self.network = network
        self.service_group = service_group
        self.service_name = service_name
        self.access_key = access_key
        self.secret_key = secret_key
        self.center_addr = center_addr
        self.ip = ip
        self.port = port

    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def register(self, vertexes):
        pass

    @abstractmethod
    def deregister(self):
        pass

    # TODO 在graph发生动态变化时调用
    @abstractmethod
    def update(self, vertexes):
        pass

    @abstractmethod
    def get_service(self, service_name, service_group) -> [VertexConfig]:
        pass

    @abstractmethod
    def list_service(self) -> [VertexConfig]:
        pass

    @abstractmethod
    def release(self):
        pass

    def register_vertexes(self, vertexes_configs: list[VertexConfig]):
        third_party_vertexes = [ThirdPartyGroupVertex(self.network,
                                                      ThirdPartyExecutable(
                                                          vertex_config.name,
                                                          vertex_config.title,
                                                          vertex_config.description,
                                                          vertex_config.service_group,
                                                          vertex_config.service_name, vertex_config.ip,
                                                          vertex_config.port,
                                                          vertex_config.type,
                                                      ),
                                                      vertex_config.params,
                                                      vertex_config.results) if vertex_config.name == vertex_config.service_name else
                                ThirdPartyAgentVertex(self.network,
                                                      ThirdPartyExecutable(
                                                          vertex_config.name,
                                                          vertex_config.title,
                                                          vertex_config.description,
                                                          vertex_config.service_group,
                                                          vertex_config.service_name, vertex_config.ip,
                                                          vertex_config.port,
                                                          vertex_config.type,
                                                      ),
                                                      vertex_config.params, vertex_config.results)
                                for vertex_config in vertexes_configs]
        third_party_vertexes_map = {}
        for third_party_vertex in third_party_vertexes:
            service_name = third_party_vertex.executable.service_name
            service_group = third_party_vertex.executable.service_group
            third_party_vertexes_map.setdefault(service_name + '&&' + service_group, [])
            third_party_vertexes_map[service_name + '&&' + service_group].append(third_party_vertex)
        for service_key in third_party_vertexes_map.keys():
            service_key_splits = service_key.split('&&')
            self.network.refresh_third_party_vertexes(service_key_splits[0], service_key_splits[1],
                                                      third_party_vertexes_map[service_key])

    def update_service_vertexes(self, service_name, service_group):
        vertex_configs = self.get_service(service_name, service_group)
        self.register_vertexes(vertex_configs)

    def update_all_services_vertexes(self):
        vertex_configs = self.list_service()
        self.register_vertexes(vertex_configs)
        self.recycle_update_all_services_vertexes()

    def recycle_update_all_services_vertexes(self):
        def recycle_list_service():
            while True:
                vertex_configs = self.list_service()
                self.register_vertexes(vertex_configs)
                time.sleep(5)

        update_all_thread = threading.Thread(target=recycle_list_service)
        update_all_thread.start()

    def get_metadata(self, vertexes):
        metadata = []
        for vertex in vertexes:
            if isinstance(vertex, AgentVertex):
                metadata.append({
                    "name": vertex.name,
                    "description": vertex.description,
                    "title": vertex.title,
                    "params": vertex.params,
                    "results": vertex.results,
                    "ip": self.ip,
                    "port": self.port
                })
            elif isinstance(vertex, GroupVertex):
                metadata.append({
                    "name": vertex.name,
                    "description": vertex.description,
                    "title": vertex.title,
                    "params": vertex.params,
                    "results": vertex.results,
                    "ip": self.ip,
                    "port": self.port,
                    "type": vertex.type
                })
        return json.dumps(metadata)
