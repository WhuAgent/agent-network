# agent-network
An Agent Self-Organizing Intelligent Network.

## 环境要求

Python 版本：`3.10` 。


## 安装说明

最新稳定版本：

```
pip install git+https://github.com/WhuAgent/agent-network.git@66900a7ee6f887d076e47ef5c26c33e3e8cf07fd
```

## 更新说明

### 20241220

实现了对话历史与 network 分离，储存在 graph 里，并且能够统计对话消耗 token。

对消息格式进行了规范化，定义了 `SystemMessage`、`UserMessage`、`AssistantMessage` 和 `OpanAIMessage`。其中 `OpanAIMessage` 专指大模型返回的消息，而 `AssistantMessage` 可以指任何其他消息（主要用于日志记录）。

#### BaseAgent.initial_system_message()

现在的 agent 不再需要重写 `init_messages` 方法，`init_messages` 方法被修改为 `initial_system_message`，专门用于初始化 agent 的 system prompt。目前提供的 system prompt 初始化方式只有一种，即在配置文件里配置如下字段：

```
prompts:
  - type: "inline"
    role: "system"
    content: <your system prompt>
```

#### BaseAgent.forward()

由于对话历史和 graph 分离，而 agent 又被储存在 graph 里，所以现在需要通过参数的形式传递历史消息。具体来说，`forward` 方法现在接收两个参数 `messages` 和 `**kwargs`，其中 `messages` 是本 agent 的历史对话记录，而 `**kwargs` 还是 yaml 文件中定义的 agent 从上下文中获取的参数。

对应地，agent 也要返回两个返回值，新的历史消息记录 `messages` 和 agent 要输出到上下文中的结果 `results`。

`BaseAgent` 类定义了一个方法 `add_message()`，用来向历史消息列表中添加一条消息，并返回新的列表。`BaseAgent.chat_llm()` 方法会自动在大模型返回之后调用 `add_message()`，因此在 `forward()` 方法中，调用 `cghat_llm()` 之后不再需要通过 `add_message()` 方法添加消息。

### 20241026

如果需要调用大模型，请直接使用 BaseAgent 提供的 `self.chat_llm` 方法，只有通过该方法进行的大模型调用才能被记录（token 和成本）。

## TODO

- [ ] 添加新的 system prompt 初始化方式，如根据 role、goal、context 等信息生成。
- [ ] 支持更多的模型。