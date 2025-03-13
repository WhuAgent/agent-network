import threading

from agent_network.graph.graph import Graph
from flask import Flask, request
from agent_network.constant import network, logger

app = Flask(__name__)


@app.route('/service', methods=['POST'])
def service():
    context = request.json
    assert context['flowId'] is not None, "智能体流程节点未找到"
    assert context['task'] is not None, "智能体任务未找到"
    graph = Graph(logger)
    graph.execute(network, context['flowId'], context['params'])
    result = graph.retrieve_results()
    graph.release()
    return result


def run_web(debug=False):
    app.run(host='0.0.0.0', port=18080, debug=debug)


if __name__ == '__main__':
    web_thread = threading.Thread(target=run_web)
    web_thread.start()
