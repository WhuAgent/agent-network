# agent-network
An Agent Self-Organizing Intelligent Network.

## 环境要求

Python 版本：`3.10` 。

还需要在系统中运行 RabbitMQ 服务。请参考 [RabbitMQ 官方文档](https://www.rabbitmq.com/dcs/download)。

## 安装说明

首次安装：

```
pip install git+https://github.com/WhuAgent/agent-network.git
```

安装之后更新，使用 `--force-reinstall` 参数防止 `pip` 从缓存中安装。

```
pip install --force-reinstall git+https://github.com/WhuAgent/agent-network.git
```

如果需要安装特定分支的代码，如 `lornd_dev` 下的代码，则在仓库地址最后面加上 `@lornd_dev` 。

```
pip install git+https://github.com/WhuAgent/agent-network.git@lornd_dev
```