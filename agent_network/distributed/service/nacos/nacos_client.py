from v2.nacos import NacosNamingService, NacosConfigService, ConfigParam, RegisterInstanceParam, \
    DeregisterInstanceParam, Instance, SubscribeServiceParam, ListServiceParam, GetServiceParam
from v2.nacos.common.client_config import ClientConfig

from agent_network.distributed.client import Client
from agent_network.distributed.service_config import NodeConfig
import json


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

    def connect(self):
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

    def register(self, nodes):
        metadata = self.get_metadata(nodes)
        res = await self.config_client.publish_config(ConfigParam(
            data_id=self.service_name,
            group=self.service_group,
            content=metadata)
        )
        await self.naming_client.register_instance(
            request=RegisterInstanceParam(
                service_name=self.service_name,
                group_name=self.service_group,
                ip=self.ip,
                port=self.port,
                weight=1.0,
                cluster_name='c1',
                metadata=metadata,
                enabled=True,
                healthy=True,
            )
        )

    def deregister(self):
        res = await self.config_client.remove_config(ConfigParam(
            data_id=self.service_name,
            group=self.service_group
        ))
        response = await self.naming_client.deregister_instance(
            request=DeregisterInstanceParam(
                service_name=self.service_name,
                group_name=self.service_group,
                ip=self.ip,
                port=self.port,
                cluster_name='c1',
            )
        )
        for service in self.subscribed_service:
            await self.config_client.remove_listener(service, self.service_group, self.config_listener)
        self.subscribed_service.clear()

    def update(self, nodes):
        metadata = self.get_metadata(nodes)
        response = await self.naming_client.update_instance(
            request=RegisterInstanceParam(
                service_name=self.service_name,
                group_name=self.service_group,
                ip=self.ip,
                port=self.port,
                weight=2.0,
                cluster_name='c1',
                metadata=metadata,
                enabled=True,
                healthy=True
            )
        )

    def get_service(self, service_name, service_group) -> [NodeConfig]:
        service = await self.naming_client.get_service(
            GetServiceParam(service_name=service_name, group_name=service_group, cluster_name='c1'))
        if service not in self.subscribed_service:
            await self.config_client.add_listener(service, self.service_group, self.config_listener)
            self.subscribed_service.append(service)
        node_configs = self.get_node_configs(service)
        return node_configs

    def list_service(self) -> [NodeConfig]:
        service_list = await self.naming_client.list_services(ListServiceParam())
        nodes_configs = []
        for service in service_list:
            nodes_configs.extend(self.get_node_configs(service))
            if service not in self.subscribed_service:
                await self.config_client.add_listener(service, self.service_group, self.config_listener)
                self.subscribed_service.append(service)
        return nodes_configs

    def release(self):
        self.deregister()
        await self.naming_client.shutdown()
        await self.config_client.shutdown()

    def get_node_configs(self, service):
        return self.loads_config(await self.config_client.get_config(ConfigParam(
            data_id=service,
            group=self.service_group
        )), service)

    def loads_config(self, content, service):
        node_configs: list[NodeConfig] = json.loads(content)
        for node_config in node_configs:
            node_config.service_name = service
            node_config.service_group = self.service_group
        return node_configs
