import signal
import os
import yaml
from agent_network.distributed.service.nacos.nacos_client import NacosClient

service_configs = []
service_config_path = os.path.join(os.getcwd(), 'agent_network/config/service.yml')
if os.path.exists(service_config_path):
    with open(service_config_path, "r", encoding="UTF-8") as f:
        service_config = yaml.safe_load(f)
        service_configs.append(service_config)

def signal_handler(sig, frame):
    if service_client is not None:
        service_client.release()


signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
signal.signal(signal.SIGTERM, signal_handler)  # kill
