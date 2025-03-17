from agent_network.network.network import Network
import agent_network.utils.micropython as mp
import ujson
import uos
from agent_network.utils.logger import Logger
from agent_network.distributed.service.nacos.nacos_client import NacosClient
import uasyncio as asyncio
import esp32_init

logger = Logger("log")
network = Network('agent-network', None, None, None, logger)


def load():
    try:
        service_configs = []
        service_clients = []
        print(uos.listdir())
        service_config_path = mp.path_join(uos.getcwd(), 'config/service.json')
        if mp.path_exists(service_config_path):
            with open(service_config_path, "r", encoding="UTF-8") as f:
                service_config = ujson.load(f)
                service_configs.append(service_config)
        for service_config in service_configs:
            if "wifi" in service_config and "password" in service_config:
                esp32_init.init(service_config["wifi"], service_config["password"])
            if 'center_type' in service_config:
                pass
            elif 'enabled' in service_config and not bool(service_config['enabled']):
                continue
            else:
                service_client = NacosClient(
                    network=network,
                    service_group=service_config["service_group"],
                    service_name=service_config["service_name"],
                    access_key=service_config["access_key"],
                    secret_key=service_config["secret_key"],
                    center_addr=service_config["center_addr"],
                    ip=service_config["ip"],
                    port=service_config["port"],
                )
                loop = asyncio.get_event_loop()
                loop.run_until_complete(service_client.connect())
                # service_client.update_all_services_vertexes()
                service_clients.append(service_client)
        network.register_clients(service_clients)
        network.load("config/network.json")
    except Exception as e:
        print(f"Agent-network load error, please check config file: {e}")
        network.release()
        # _exit(0)


load()
