# from v2.nacos import NacosNamingService, NacosConfigService, ConfigParam, RegisterInstanceParam, \
#     DeregisterInstanceParam, Instance, SubscribeServiceParam, ListServiceParam, GetServiceParam
# from v2.nacos.common.client_config import ClientConfig
import nacos
from agent_network.distributed.client import Client
from agent_network.distributed.service_config import NodeConfig
import json
import requests
import time
import threading


class NacosClient(Client):
    def __init__(self, graph, service_group, service_name, access_key, secret_key, center_addr, ip, port):
        super().__init__(graph, service_group, service_name, access_key, secret_key, center_addr, ip, port)
        self.naming_client = None
        self.config_client = None
        self.subscribed_service = []

    async def config_listener(self, tenant, data_id, group, content):
        print("listen, tenant:{} data_id:{} group:{} content:{}".format(tenant, data_id, group, content))
        listened_node_configs = self.loads_config(content, data_id)
        self.register_nodes(listened_node_configs)

    async def connect(self):
        # self.naming_client = await NacosNamingService.create_naming_service(ClientConfig(
        #     server_addresses=self.center_addr,
        #     access_key=self.access_key,
        #     secret_key=self.secret_key,
        # ))
        # self.config_client = await NacosConfigService.create_config_service(ClientConfig(
        #     server_addresses=self.center_addr,
        #     access_key=self.access_key,
        #     secret_key=self.secret_key,
        # ))
        self.nacos_client = nacos.NacosClient(self.center_addr)

    async def register(self, nodes):
        metadata = self.get_metadata(nodes)
        self.nacos_client.publish_config(self.service_name, self
                                         .service_group, metadata)
        # await self.config_client.publish_config(ConfigParam(
        #     data_id=self.service_name,
        #     group=self.service_group,
        #     content=metadata)
        # )
        # await self.naming_client.register_instance(
        #     request=RegisterInstanceParam(
        #         service_name=self.service_name,
        #         group_name=self.service_group,
        #         ip=self.ip,
        #         port=self.port,
        #         weight=1.0,
        #         # cluster_name='c1',
        #         # metadata=metadata,
        #         enabled=True,
        #         healthy=True,
        #     )
        # )
        result = await self.service_register()
        if not result:
            print(f"nacos register failed with addr: {self.center_addr}")
            return
        await self.service_beat()

    async def service_register(self):
        url = f"{self.center_addr}/nacos/v2/ns/instance?serviceName={self.service_name}&groupName={self.service_group}&ip={self.ip}&port={self.port}"
        res = requests.post(url)
        return res.status_code == 200

    async def service_beat(self):
        def heart_beat():
            while True:
                url = f"{self.center_addr}/nacos/v1/ns/instance/beat?serviceName={self.service_name}&groupName={self.service_group}&ip={self.ip}&port={self.port}"
                res = requests.put(url)
                if res.status_code != 200:
                    print(f"nacos heart beat failed with addr: {self.center_addr}")
                time.sleep(5)

        send_beat_thread = threading.Thread(target=heart_beat)
        send_beat_thread.start()

    def search_service(self, service_name, service_group):
        url = f"{self.center_addr}/nacos/v2/ns/service?serviceName={service_name}&&groupName={service_group}"
        res = requests.get(url)
        # if
        return res.status_code == 200

    def search_services(self, service_group):
        url = f"{self.center_addr}/nacos/v2/ns/service/list?groupName={service_group}"
        res = requests.get(url)
        # if
        return res.json()['data']

    async def deregister(self):
        self.nacos_client.remove_config(self.service_name, self.service_group)
        self.nacos_client.remove_naming_instance(self.service_name, self.ip, self.port, group_name=self.service_group)
        for service in self.subscribed_service:
            self.nacos_client.remove_config_watcher(service, self.service_group, self.config_listener)
        # await self.config_client.remove_config(ConfigParam(
        #     data_id=self.service_name,
        #     group=self.service_group
        # ))
        # await self.naming_client.deregister_instance(
        #     request=DeregisterInstanceParam(
        #         service_name=self.service_name,
        #         group_name=self.service_group,
        #         ip=self.ip,
        #         port=self.port,
        #         # cluster_name='c1',
        #     )
        # )
        # for service in self.subscribed_service:
        #     await self.config_client.remove_listener(service, self.service_group, self.config_listener)
        self.subscribed_service.clear()

    async def update(self, nodes):
        metadata = self.get_metadata(nodes)
        self.nacos_client.publish_config(self.service_name, self
                                         .service_group, metadata)
        self.nacos_client.modify_naming_instance(self.service_name, self.ip, self.port, group_name=self.service_group)
        # await self.config_client.publish_config(ConfigParam(
        #     data_id=self.service_name,
        #     group=self.service_group,
        #     content=metadata)
        # )
        # await self.naming_client.update_instance(
        #     request=RegisterInstanceParam(
        #         service_name=self.service_name,
        #         group_name=self.service_group,
        #         ip=self.ip,
        #         port=self.port,
        #         weight=1.0,
        #         # cluster_name='c1',
        #         # metadata=metadata,
        #         enabled=True,
        #         healthy=True
        #     )
        # )

    def get_service(self, service_name, service_group) -> [NodeConfig]:
        # service = asyncio.get_event_loop().run_until_complete(self.naming_client.get_service(
        #     GetServiceParam(service_name=service_name, group_name=service_group)))
        # self.nacos_client.get_naming_instance(self.service_name, self.ip,)
        if not self.search_service(service_name, service_group):
            return []
        if service_name not in self.subscribed_service:
            # asyncio.get_event_loop().run_until_complete(
            #     self.config_client.add_listener(service, self.service_group, self.config_listener))
            self.nacos_client.add_config_watcher(service_name, service_group, self.config_listener)
            self.subscribed_service.append(service_name)
        node_configs = self.get_node_configs(service_name)
        return node_configs

    def list_service(self) -> [NodeConfig]:
        # service_list = asyncio.get_event_loop().run_until_complete(self.naming_client.list_services(ListServiceParam()))
        service_list = self.search_services(self.service_group)
        nodes_configs = []
        if service_list['count'] > 0:
            for service in service_list['services']:
                if service == self.service_name: continue
                nodes_configs.extend(self.get_node_configs(service))
                if service not in self.subscribed_service:
                    # asyncio.get_event_loop().run_until_complete(
                    #     self.config_client.add_listener(service, self.service_group, self.config_listener))
                    self.nacos_client.add_config_watcher(service, self.service_group, self.config_listener)
                    self.subscribed_service.append(service)
        return nodes_configs

    async def release(self):
        await self.deregister()
        await self.naming_client.shutdown()
        await self.config_client.shutdown()

    def get_node_configs(self, service):
        # return self.loads_config(asyncio.get_event_loop().run_until_complete(self.config_client.get_config(ConfigParam(
        #     data_id=service,
        #     group=self.service_group
        # ))), service)
        return self.loads_config(self.nacos_client.get_config(service, self.service_group), service)

    def loads_config(self, content, service):
        node_configs_list = json.loads(content)
        node_configs = []
        for node_config in node_configs_list:
            nc = NodeConfig(node_config["name"], node_config["description"],
                            node_config["task"], node_config["params"],
                            node_config["results"], node_config["ip"], node_config["port"])
            nc.service_name = service
            nc.service_group = self.service_group
            node_configs.append(nc)
        return node_configs
