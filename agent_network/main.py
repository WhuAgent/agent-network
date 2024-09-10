from pipeline.pipeline import Pipeline
from utils.logger import Logger

if __name__ == '__main__':
    config_dir = ""
    logger = Logger("log")
    pipeline = Pipeline(config_dir, logger)
    pipeline.agent()
