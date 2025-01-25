from agent_network.network.network import Network
from agent_network.network.graph import Graph
import os
import yaml
from agent_network.utils.logger import Logger
from agent_network.distributed.service.nacos.nacos_client import NacosClient

logger = Logger("log")
network = Network('agent-network', None, None, None)
graph = Graph('graph', None, None, None, None, None, logger)
service_configs = []
service_clients = []
service_config_path = os.path.join(os.getcwd(), 'agent_network/config/service.yml')
if os.path.exists(service_config_path):
    with open(service_config_path, "r", encoding="UTF-8") as f:
        service_config = yaml.safe_load(f)
        service_configs.append(service_config)
for service_config in service_configs:
    if 'center_type' in service_config:
        pass
    else:
        service_client = NacosClient(
            graph=graph,
            service_group=service_config["service_group"],
            service_name=service_config["service_name"],
            access_key=service_config["access_key"],
            secret_key=service_config["secret_key"],
            center_addr=service_config["center_addr"],
            ip=service_config["ip"],
            port=service_config["port"],
        )
        service_client.connect()
        # service_client.update_all_services_nodes()
        service_clients.append(service_client)
graph.register_clients(service_clients)
