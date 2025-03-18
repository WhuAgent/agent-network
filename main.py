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
    graph.execute(network, context['flowId'], context.get("params"), context.get("results"))
    result = graph.retrieve_results()
    graph.release()
    return result


def run_web(debug=False):
    app.run(host='0.0.0.0', port=18080, debug=debug)


if __name__ == '__main__':
    web_thread = threading.Thread(target=run_web)
    web_thread.start()
    
"""
Example Request:

{
    "flowId": "worker",
    "task": "学校发了一个新的讲座通知，相关文件在 C:\\Users\\lornd\\Downloads\\FC804E96CF497636909FC43BE21_07186CAC_E21D4.jpg，能告诉我讲座什么时候在哪里举行，是有关于什么的讲座吗？",
    "params": {},
    "results": {
        "result": "讲座相关信息"
    }
}
"""
