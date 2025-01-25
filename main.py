import threading

from agent_network.pipeline.pipeline import Pipeline
from flask import Flask, request
from agent_network.constant import graph, logger

app = Flask(__name__)


@app.route('/task', methods=['GET'])
def task():
    current_task = request.args.get('task')
    pipeline = Pipeline(current_task, logger)
    pipeline.execute(graph, current_task, start_node="")
    result = pipeline.retrieve_results()
    pipeline.release()
    return result


@app.route('/service', methods=['POST'])
def task():
    task = request.args.get('task')
    node = request.args.get('node')
    context = request.json()
    pipeline = Pipeline(task, logger)
    pipeline.execute(graph, task, node, context)
    result = pipeline.retrieve_results()
    pipeline.release()
    return result


def run_web(debug=False):
    app.run(host='0.0.0.0', port=18080, debug=debug)


if __name__ == '__main__':
    web_thread = threading.Thread(target=run_web)
    web_thread.start()
