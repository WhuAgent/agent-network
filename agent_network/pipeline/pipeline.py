import importlib
import json
import yaml

from agent_network.pipeline.config.config_loader import AgentConfig, GroupConfig
from agent_network.pipeline.node import Node, GroupNode, TaskNode
from agent_network.base import BaseGroup
import os


class Pipeline:
    def __init__(self, config_file_path, logger):
        with open(config_file_path, "r", encoding="UTF-8") as f:
            self.config = yaml.safe_load(f)
        self.logger = logger
        self.nodes = []
        self.global_context = self.config["context"]
        self.load()

    def load(self):
        configs = []
        for group in self.config["group_pipline"]:
            group_name, group_config_path = list(group.items())[0]
            self.nodes.append(BaseGroup(group_config_path, self.logger, self.global_context))
        # for root, dirs, files in os.walk(self.config_dir):
        #     for dir in dirs:
        #         if dir.endswith("Agent"):
        #             agent_group_config = {}
        #             groups_config = {}
        #             agent_dir_path = os.path.join(root, dir)
        #             config_files = os.listdir(agent_dir_path)
        #             files = [file for file in config_files if os.path.isfile(os.path.join(agent_dir_path, file))]
        #             for file in files:
        #                 if file == "AgentConfig.json":
        #                     with open(os.path.join(agent_dir_path, file), "r",
        #                               encoding="utf-8") as ap:
        #                         agent_configs_dict = json.load(ap)
        #                         agent_group_config['name'] = agent_configs_dict['name']
        #                         agent_group_config['task'] = agent_configs_dict['task']
        #                         agent_group_config['loadType'] = agent_configs_dict['loadType']
        #                         if agent_group_config['loadType'] == 'module':
        #                             if 'loadModule' in agent_configs_dict:
        #                                 agent_group_config['loadModule'] = agent_configs_dict['loadModule']
        #                             else:
        #                                 raise Exception(f'loadModule do not exist with config: {agent_configs_dict}')
        #                         agent_configs = agent_configs_dict['agents']
        #                         agent_group_config['agents'] = [AgentConfig.agent_decoder(agent_config)
        #                                                         for agent_config in agent_configs]
        #                 if "GroupConfig.json" == file:
        #                     with open(os.path.join(agent_dir_path, file), "r",
        #                               encoding="utf-8") as gp:
        #                         group_configs_dict = json.load(gp)
        #                         groups_config['groups'] = [GroupConfig.group_decoder(group_config)
        #                                                    for group_config in group_configs_dict['groups']]
        #                         groups_config['name'] = group_configs_dict['name']
        #                         groups_config['task'] = group_configs_dict['task']
        #             configs.append({"agent_config": agent_group_config, "group_config": groups_config})
        # return configs

    def design_agent_group(self, agent_group_config: dict) -> [Node]:
        nodes = []
        if agent_group_config['loadType'] == 'module':
            load_module = importlib.import_module(agent_group_config['loadModule'])
            for agent_config in agent_group_config['agents']:
                agent_class = getattr(load_module, agent_config.name)
                agent_instance = agent_class(self.logger, agent_config.title, agent_config.task, agent_config.role,
                                             agent_config.description, agent_config.history_number,
                                             agent_config.prompts,
                                             agent_config.tools, agent_config.runtime_revision_number,
                                             **agent_config.init_extra_params
                                             )
                agent_children = None
                if agent_config.if_leaf and agent_config.children and len(agent_config.children) > 0:
                    agent_children = [self.design_agent_group(child) for child in agent_config.children]
                agent_node = Node(agent_instance, agent_children)
                nodes.append(agent_node)
        return nodes

    def forward(self, current_task):
        for node in self.nodes:
            node.forward(current_task=current_task)
        # configs = self.load()
        # agents_configs = [config["agent_config"] for config in configs]
        # candidate_nodes: dict[str, Node] = {}
        # candidate_task_nodes: [Node] = []
        # for agents_config in agents_configs:
        #     nodes = self.design_agent_group(agents_config)
        #     candidate_nodes[agents_config["name"]] = GroupNode(nodes, agents_config["name"], agents_config["task"])
        #
        # groups_configs = [config["group_config"] for config in configs]
        # for groups_config in groups_configs:
        #     candidate_group_nodes: dict[str, [Node]] = {}
        #     for group in groups_config["groups"]:
        #         if group["agentsRef"] in candidate_task_nodes:
        #             if group["name"] not in candidate_group_nodes:
        #                 candidate_group_nodes[group["name"]] = []
        #                 candidate_group_nodes[group["name"]].append(candidate_task_nodes[group["agentsRef"]])
        #     candidate_task_nodes.append(TaskNode(candidate_group_nodes.values(), groups_config["name"], groups_config["task"]))
        # for candidate_task_node in candidate_task_nodes:
        #     candidate_task_node.execute(candidate_task_node.task)
