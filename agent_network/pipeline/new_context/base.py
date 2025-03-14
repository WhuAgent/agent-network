from agent_network.pipeline.history import History
from agent_network.utils.llm.message import Message

class BaseContext:
    def __init__(self, logger, **kwargs):
        self.logger = logger
        
        self.task = None

        for key, value in kwargs.items():
            setattr(self, key, value)
        
        self.total_time = 0
        self.message_num = 0
        self.execution_history: list[History] = []
        self.cur_execution: History = None
        self.node_messages = dict()

    def retrieve(self, attr_name: str, default=None):
        # 直接返回属性值，若属性不存在则返回 default 值（默认抛出 AttributeError）
        return getattr(self, attr_name, default)
    
    def retrieve_all(self):
        return self.__dict__
    
    def register(self, key, value):
        setattr(self, key, value)

    def reset(self):
        pass

    def register_time(self, time_cost):
        self.cur_execution.time_cost = time_cost

        self.total_time += time_cost

        self.logger.log("network", 
                        f"AGENT {self.cur_execution.cur_executor.name} time cost: {time_cost}", "Agent-Network")
        
    def register_llm_action(self, messages: list[Message]):
        node = self.cur_execution.cur_executor.name

        for i in range(len(self.node_messages[node]), len(messages)):
            self.node_messages[node].append(messages[i])
        
        for i in range(self.message_num, len(messages)):
            self.cur_execution.llm_messages.append(messages[i])
            self.message_num += 1

    def add_message(self, node, message):
        if node in self.node_messages.keys():
            self.node_messages[node].append(message)
        else:
            self.node_messages[node] = [message]

    def retrieve_messages(self, node):
        return self.node_messages.get(node, [])
    
    def register_execution_history(self, record):
        self.execution_history.append(record)
        self.cur_execution = self.execution_history[-1]

    def summarize_time(self):
        return self.total_time

    def summarize_llm_action(self):
        total_token_num = 0
        total_token_cost = 0

        for execution in self.execution_history:
            for message in execution.llm_messages:
                total_token_num += message.token_num
                total_token_cost += message.token_cost

        return total_token_num, total_token_cost
    
    def summary(self):
        return self.summarize_llm_action(), self.summarize_time()