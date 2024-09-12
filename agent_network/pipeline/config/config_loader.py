from __future__ import annotations


class PromptsConfig:
    def __init__(self, type: str, contents: [str]):
        self.type = type
        self.contents = contents


def prompts_decoder(obj: dict):
    if 'type' in obj and 'contents' in obj:
        return PromptsConfig(obj['type'], obj['contents'])
    raise Exception(f'prompt config illegal: {obj}')


class ToolsConfig:
    def __init__(self, name: str, type: str):
        self.name = name
        self.type = type


def tools_decoder(obj: dict):
    if 'type' in obj and 'name' in obj:
        return PromptsConfig(obj['name'], obj['type'])
    raise Exception(f'tools config illegal: {obj}')


class AgentConfig:
    def __init__(self, name: str, title: str, description: str, task: str, role: str, if_leaf: bool,
                 prompts: [PromptsConfig], tools: [ToolsConfig] = None, children: [AgentConfig] = None,
                 if_knowledgeable: bool = False, if_learnable: bool = False, if_service: bool = False,
                 runtime_revision_number: int = 0, history_number: int = 0, energy: int = 0,
                 init_extra_params: dict = {}):
        self.name = name
        self.title = title
        self.description = description
        self.task = task
        self.if_leaf = if_leaf
        self.if_service = if_service
        self.if_knowledgeable = if_knowledgeable
        self.if_learnable = if_learnable
        self.runtime_revision_number = runtime_revision_number
        self.history_number = history_number
        self.energy = energy
        self.role = role
        self.prompts = prompts
        self.tools = tools
        self.children = children
        self.init_extra_params = init_extra_params


def agent_decoder(obj: dict):
    if 'description' in obj and 'title' in obj and 'name' in obj and 'ifLeaf' in obj and 'role' in obj \
            and 'prompts' in obj and 'task' in obj:
        return AgentConfig(obj['name'], obj['title'], obj['description'], obj['task'], obj['role'], obj['ifLeaf'],
                           obj['prompts'],
                           obj['tools'] if 'tools' in obj else None,
                           [agent_decoder(child) for child in obj['children']] if 'children' in obj and len(
                               obj['children']) > 0 else None,
                           obj['ifKnowledgeable'] if 'ifKnowledgeable' in obj else None,
                           obj['ifLearnable'] if 'ifLearnable' in obj else None,
                           obj['ifService'] if 'ifService' in obj else None,
                           obj['runtimeRevisionNumber'] if 'runtimeRevisionNumber' in obj else None,
                           obj['historyNumber'] if 'historyNumber' in obj else None,
                           obj['energy'] if 'energy' in obj else None,
                           obj['initExtraParams'] if 'initExtraParams' in obj else None,
                           )
    raise Exception(f'agent config illegal: {obj}')


class GroupConfig:
    def __init__(self, name: str, description: str, task: str, if_leaf: bool, agents_ref: str,
                 prompts: [PromptsConfig], tools: [ToolsConfig] = None, children: [GroupConfig] = None,
                 if_knowledgeable: bool = False, if_learnable: bool = False, if_service: bool = False,
                 runtime_revision_number: int = 0, history_number: int = 0, energy: int = 0):
        self.name = name
        self.description = description
        self.task = task
        self.if_leaf = if_leaf
        self.if_service = if_service
        self.if_knowledgeable = if_knowledgeable
        self.if_learnable = if_learnable
        self.runtime_revision_number = runtime_revision_number
        self.history_number = history_number
        self.energy = energy
        self.prompts = prompts
        self.tools = tools
        self.children = children
        self.agents_ref = agents_ref


def group_decoder(obj: dict):
    if 'description' in obj and 'name' in obj and 'ifLeaf' in obj and 'agentsRef' in obj \
            and 'prompts' in obj and 'task' in obj:
        return GroupConfig(obj['name'], obj['description'], obj['task'], obj['ifLeaf'], obj['agentsRef'],
                           obj['prompts'],
                           obj['tools'] if 'tools' in obj else None,
                           [group_decoder(child) for child in obj['children']] if 'children' in obj and len(
                               obj['children']) > 0 else None,
                           obj['ifKnowledgeable'] if 'ifKnowledgeable' in obj else None,
                           obj['ifLearnable'] if 'ifLearnable' in obj else None,
                           obj['ifService'] if 'ifService' in obj else None,
                           obj['runtimeRevisionNumber'] if 'runtimeRevisionNumber' in obj else None,
                           obj['historyNumber'] if 'historyNumber' in obj else None,
                           obj['energy'] if 'energy' in obj else None,
                           )
    raise Exception(f'group config illegal: {obj}')
