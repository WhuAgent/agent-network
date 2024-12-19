# agent-network
An Agent Self-Organizing Intelligent Network.

## 环境要求

Python 版本：`3.10` 。


## 安装说明

最新稳定版本：

```
pip install git+https://github.com/WhuAgent/agent-network.git@46dd2cb70289eafae12d1d77ae3d6cf23ecb8f17
```

## 使用说明

如果需要调用大模型，请直接使用 BaseAgent 提供的 `self.chat_llm` 方法，只有通过该方法进行的大模型调用才能被记录（token 和成本）。