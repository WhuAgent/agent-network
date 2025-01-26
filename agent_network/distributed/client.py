import json
import time
from abc import abstractmethod
from agent_network.network.graph import Graph
from agent_network.distributed.service.service_config import NodeConfig
from agent_network.network.nodes.node import ThirdPartyNode
from agent_network.network.nodes.third_party.executable import ThirdPartyExecutable
import threading


class Client:
    def __init__(self, graph: Graph, service_group, service_name, access_key, secret_key, center_addr, ip, port):
        self.graph = graph
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
    def register(self, nodes):
        pass

    @abstractmethod
    def deregister(self):
        pass

    # TODO 在graph发生动态变化时调用
    @abstractmethod
    def update(self, nodes):
        pass

    @abstractmethod
    def get_service(self, service_name, service_group) -> [NodeConfig]:
        pass

    @abstractmethod
    def list_service(self) -> [NodeConfig]:
        pass

    @abstractmethod
    def release(self):
        pass

    def register_nodes(self, nodes_configs: list[NodeConfig]):
        third_party_nodes = [ThirdPartyNode(self.graph,
                                            ThirdPartyExecutable(
                                                node_config.name, node_config.task,
                                                node_config.description, node_config.service_group,
                                                node_config.service_name, node_config.ip, node_config.port
                                            ),
                                            node_config.params, node_config.results)
                             for node_config in nodes_configs]
        third_party_nodes_map = {}
        for third_party_node in third_party_nodes:
            service_name = third_party_node.executable.service_name
            service_group = third_party_node.executable.service_group
            third_party_nodes_map.setdefault(service_name + '&&' + service_group, [])
            third_party_nodes_map[service_name + '&&' + service_group].append(third_party_node)
        for service_key in third_party_nodes_map.keys():
            service_key_splits = service_key.split('&&')
            self.graph.refresh_third_party_nodes(service_key_splits[0], service_key_splits[1],
                                                 third_party_nodes_map[service_key])

    def update_service_nodes(self, service_name, service_group):
        node_configs = self.get_service(service_name, service_group)
        self.register_nodes(node_configs)

    def update_all_services_nodes(self):
        node_configs = self.list_service()
        self.register_nodes(node_configs)
        self.recycle_update_all_services_nodes()

    def recycle_update_all_services_nodes(self):
        def recycle_list_service():
            while True:
                node_configs = self.list_service()
                self.register_nodes(node_configs)
                time.sleep(5)

        update_all_thread = threading.Thread(target=recycle_list_service)
        update_all_thread.start()

    def get_metadata(self, nodes):
        metadata = [
            {
                "name": node.name,
                "description": node.description,
                "task": node.task,
                "params": node.params,
                "results": node.results,
                "ip": self.ip,
                "port": self.port
            }
            for node in nodes
        ]
        return json.dumps(metadata)
