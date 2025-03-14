# agent-network
An Agent Self-Organizing Intelligent Network.

## 环境要求

Python 版本：`3.10` 。


## 安装说明

最新稳定版本：

```
pip install git+https://github.com/WhuAgent/agent-network.git@ITER_20250308_FLOW
```

## 编写智能体

### 智能体配置及智能体组配置

见agent_network/config文件夹下

### 编写智能体代码逻辑

在agent.py下编写
```python
# 继承BaseAgent，智能体名称：Agent1必须和配置文件前缀一致，否则无法顺利加载
class Agent1(BaseAgent):
    def __init__(self, graph, config, logger):
        super().__init__(graph, config, logger)

    def forward(self, message, **kwargs):
        # kwargs对应配置文件params
        messages = []
        self.add_message("user", f"number1: {kwargs['number1']} number2: {kwargs['number2']}", messages)
        # 调用大模型
        response = self.chat_llm(messages)
        print('response: ' + response.content)
        result = int(kwargs['number1']) + int(kwargs['number2'])
        # 对应配置文件results
        results = {
            "bool_result": '1',
            "result": result,
        }
        return messages, results
```
