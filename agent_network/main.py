from pipeline.pipeline import Pipeline
from utils.logger import Logger

if __name__ == '__main__':
    task = ""
    config_dir = "config/pipline/open_document_and_input.yaml"

    logger = Logger("log")

    pipeline = Pipeline(config_dir, logger)
    pipeline.forward(task)
