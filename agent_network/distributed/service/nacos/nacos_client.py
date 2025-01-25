from v2.nacos import NacosNamingService, NacosConfigService, ConfigParam, RegisterInstanceParam, \
    DeregisterInstanceParam, Instance, SubscribeServiceParam, ListServiceParam, GetServiceParam
from v2.nacos.common.client_config import ClientConfig

from agent_network.distributed.client import Client
from agent_network.distributed.service_config import NodeConfig
import json
import asyncio


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
        self.naming_client = await NacosNamingService.create_naming_service(ClientConfig(
            server_addresses=self.center_addr,
            access_key=self.access_key,
            secret_key=self.secret_key,
        ))
        self.config_client = await NacosConfigService.create_config_service(ClientConfig(
            server_addresses=self.center_addr,
            access_key=self.access_key,
            secret_key=self.secret_key,
        ))

    async def register(self, nodes):
        metadata = self.get_metadata(nodes)
        await self.config_client.publish_config(ConfigParam(
            data_id=self.service_name,
            group=self.service_group,
            content=metadata)
        )
        await self.naming_client.register_instance(
            request=RegisterInstanceParam(
                service_name=self.service_name,
                # group_name=self.service_group,
                ip=self.ip,
                port=self.port,
                weight=1.0,
                # cluster_name='c1',
                # metadata=metadata,
                enabled=True,
                healthy=True,
            )
        )

    async def deregister(self):
        await self.config_client.remove_config(ConfigParam(
            data_id=self.service_name,
            group=self.service_group
        ))
        await self.naming_client.deregister_instance(
            request=DeregisterInstanceParam(
                service_name=self.service_name,
                group_name=self.service_group,
                ip=self.ip,
                port=self.port,
                # cluster_name='c1',
            )
        )
        for service in self.subscribed_service:
            await self.config_client.remove_listener(service, self.service_group, self.config_listener)
        self.subscribed_service.clear()

    async def update(self, nodes):
        metadata = self.get_metadata(nodes)
        await self.config_client.publish_config(ConfigParam(
            data_id=self.service_name,
            group=self.service_group,
            content=metadata)
        )
        await self.naming_client.update_instance(
            request=RegisterInstanceParam(
                service_name=self.service_name,
                group_name=self.service_group,
                ip=self.ip,
                port=self.port,
                weight=1.0,
                # cluster_name='c1',
                # metadata=metadata,
                enabled=True,
                healthy=True
            )
        )

    def get_service(self, service_name, service_group) -> [NodeConfig]:
        service = asyncio.get_event_loop().run_until_complete(self.naming_client.get_service(
            GetServiceParam(service_name=service_name, group_name=service_group)))
        if service not in self.subscribed_service:
            asyncio.get_event_loop().run_until_complete(
                self.config_client.add_listener(service, self.service_group, self.config_listener))
            self.subscribed_service.append(service)
        node_configs = self.get_node_configs(service)
        return node_configs

    def list_service(self) -> [NodeConfig]:
        service_list = asyncio.get_event_loop().run_until_complete(self.naming_client.list_services(ListServiceParam()))
        nodes_configs = []
        if service_list.count > 0:
            for service in service_list.services:
                if service == self.service_name: continue
                nodes_configs.extend(self.get_node_configs(service))
                if service not in self.subscribed_service:
                    asyncio.get_event_loop().run_until_complete(
                        self.config_client.add_listener(service, self.service_group, self.config_listener))
                    self.subscribed_service.append(service)
        return nodes_configs

    async def release(self):
        await self.deregister()
        await self.naming_client.shutdown()
        await self.config_client.shutdown()

    def get_node_configs(self, service):
        return self.loads_config(asyncio.get_event_loop().run_until_complete(self.config_client.get_config(ConfigParam(
            data_id=service,
            group=self.service_group
        ))), service)

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
