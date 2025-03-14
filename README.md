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

详见agent_network/config文件夹下

智能体：
```json
{
  "id":"Agent1",
  "name":"Agent1",
  "title":"智能体1",
  "description":"智能体1",
  "keywords": ["微信", "签名", "微信服务号信息服务"],
  "manual":"http://wechat.com/xxxx.html",
  "prompt": "提示词",
  "model": "gpt-3.5-turbo",
  "params":[
    { "title":"number1", "name":"number1", "type":"String", "notnull":true, "description": "数字1", "defaultValue":"" },
    { "title":"number2", "name":"number2", "type":"String", "notnull":true, "description": "数字2", "defaultValue":"" }
  ],
  "results":[
    { "title":"result", "name":"result", "type":"String", "notnull":true, "description":"结果", "defaultValue":"" },
    { "title":"bool_result", "name":"bool_result", "type":"Boolean", "notnull":true, "description":"布尔结果", "defaultValue":"" }
  ]
}
```
智能体组：
```json
{
  "id":"AgentGroup1",
  "type":"python",
  "title":"获取微信服务号签名",
  "description":"获取微信服务号签名",
  "prompt": "",
  "keywords": ["微信", "签名", "微信服务号信息服务"],
  "reference":"http://xxx/Scheduling/机器ID",
  "manual":"http://wechat.com/xxxx.html",
  "agents": ["Agent1", "Agent2"],
  "params":[
    { "title":"serviceId", "name":"serviceId", "type":"String", "notnull":true, "description": "服务号ID", "defaultValue":"" }
  ],
  "results":[
    { "title":"result", "name":"result", "type":"String", "notnull":true, "description":"结果", "defaultValue":"" },
    { "title":"bool_result", "name":"bool_result", "type":"Boolean", "notnull":true, "description":"布尔结果", "defaultValue":"" }
  ]
}
```
链接
```json
{
  "group": "AgentGroup1",
  "links": [
    {
      "source": "start",
      "target": "Agent1",
      "type": "soft"
    },
    {
      "source": "Agent1",
      "target": "Agent2",
      "type": "soft"
    }
  ]
}
```

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
        # 执行错误时可能会抛出的异常
        # raise ReportError()：协作异常 / RetryError()：重试异常
        # 对应配置文件results
        results = {
            "bool_result": '1',
            "result": result,
        }
        return messages, results
```

### 配置智能体网络network.yaml
固定的配置，注册所有的智能体组
```yaml
# graph 名称
name: "AgentService1"

# graph 详细描述
description: "计算智能体网络"

# 为了完成任务的计划，通过调用 group 完成任务
groups:
  - AgentGroup1

# 任务执行过程中的上下文信息（如返回值等），用于 group 之间的信息传递
context:
  - name: "number1"
    type: "str"
  - name: "number2"
    type: "str"
  - name: "true_result"
    type: "str"
```

### 配置大模型openai.yaml
```yaml
"api_key": "sk-xxx"
"base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"
"model": "qwen2.5-32b-instruct"
```

### 配置智能体服务service.yaml
```yaml
# 服务组对应我们的graph，同一个graph的所有分布式智能体服务注册到注册中心上的同一个组，实现服务注册与发现
"service_group": "agent-network"
# 服务名是智能体功能的集合，包含当前智能体服务的所有节点，暴露为同一个微服务入口
"service_name": "agent-network-service"
"access_key": ""
"secret_key": ""
"center_addr": "http://localhost:8848"
#"center_type": "nacos"
"ip": "127.0.0.1"
"port": "18080"
"enabled": false
```
