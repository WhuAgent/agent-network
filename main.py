import threading

from agent_network.pipeline.pipeline import Pipeline
from flask import Flask, request
from agent_network.constant import graph, logger

app = Flask(__name__)


@app.route('/task', methods=['GET'])
def task():
    current_task = request.args.get('task')
    config_dir = "agent_network/config"
    pipeline = Pipeline(current_task, config_dir, logger)
    pipeline.execute(graph, current_task)
    result = pipeline.retrieve_results()
    pipeline.release()
    return result


@app.route('/service', methods=['POST'])
def task():
    current_task = request.args.get('task')
    context = request.args.get('context')
    config_dir = "agent_network/config"
    pipeline = Pipeline(current_task, config_dir, logger)
    pipeline.execute(graph, current_task, context)
    result = pipeline.retrieve_results()
    pipeline.release()
    return result


def run_web(debug=False):
    app.run(host='0.0.0.0', port=18080, debug=debug)


if __name__ == '__main__':
    web_thread = threading.Thread(target=run_web)
    web_thread.start()
