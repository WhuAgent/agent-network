
from contextvars import ContextVar

from agent_network.pipeline.new_context.base import BaseContext
from agent_network.utils.llm.message import Message


pipeline_context = ContextVar("pipeline_context", default=BaseContext)


def init(context_class, logger,  **kwargs):
    instance = context_class(logger, **kwargs)
    pipeline_context.set(instance)


def retrieve(key):
    return pipeline_context.get().retrieve(key)


def retrieves(keys):
    return {key: retrieve(key) for key in keys}

def retrieve_all():
    return pipeline_context.get().retrieve_all()


def register(key, value):
    pipeline_context.get().register(key, value)


def registers(params_map):
    for key, value in params_map.items():
        register(key, value)

def execute(action, **kwargs):
    if hasattr(pipeline_context.get(), action):
        return getattr(pipeline_context.get(), action)(**kwargs)

def reset():
    pipeline_context.get().reset()

def release():
    pass

def release_global():
    pass

def register_time(time_cost):
    pipeline_context.get().register_time(time_cost)


def register_llm_action(messages: list[Message]):
    pipeline_context.get().register_llm_action(messages)

def register_message(node, message):
    return pipeline_context.get().add_message(node, message)

def retrieve_messages(node):
    return pipeline_context.get().retrieve_messages(node)

def register_execution_history(record):
    return pipeline_context.get().register_execution_history(record)

def retrieve_execution_history():
    return pipeline_context.get().execution_history

def retrieve_cur_execution():
    return pipeline_context.get().cur_execution

def update_cur_execution(record):
    pipeline_context.get().cur_execution = record

def summary():
    return pipeline_context.get().summary()