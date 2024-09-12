from pipeline.pipeline import Pipeline
from utils.logger import Logger

if __name__ == '__main__':
    config_dir = "agent_network/config"
    current_task = "您的任务"
    logger = Logger("log")
    pipeline = Pipeline(config_dir, logger)
    pipeline.agent(current_task)
