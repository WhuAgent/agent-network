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
def service():
    context = request.json
    assert context['flowId'] is not None, "智能体流程节点未找到"
    assert context['task'] is not None, "智能体任务未找到"
    pipeline = Pipeline(context['task'], logger)
    pipeline.execute(graph, context['task'], context['flowId'], context['params'])
    result = pipeline.retrieve_results()
    pipeline.release()
    return result


def run_web(debug=False):
    app.run(host='0.0.0.0', port=18080, debug=debug)


if __name__ == '__main__':
    web_thread = threading.Thread(target=run_web)
    web_thread.start()
