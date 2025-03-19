import threading

from agent_network.graph.graph import Graph
from flask import Flask, request
from agent_network.constant import network, logger
import json

app = Flask(__name__)


@app.route('/service', methods=['POST'])
def service():
    context = request.json
    assert context['flowId'] is not None, "智能体流程节点未找到"
    assert context['task'] is not None, "智能体任务未找到"
    graph = Graph(logger)
    result = graph.execute(network, context['flowId'], context.get("params"), context.get("results", ["result"]))
    graph.release()
    return result


@app.route('/service/graph', methods=['POST'])
def service_graph():
    context = request.json
    assert context['graph'] is not None, "智能体执行图未找到"
    assert context['vertex'] is not None, "智能体流程节点未找到"
    assert context['parameterList'] is not None, "智能体流程参数未找到"
    assert context['organizeId'] is not None, "智能体流程组织架构参数未找到"
    assert context['taskId'] is not None, "智能体流程任务ID参数未找到"
    assert context['subtaskId'] is not None, "智能体流程子任务ID参数未找到"
    if "trace_id" not in context['graph']:
        Exception(f"task error: {context['graph']}")
    graph_dict = json.loads(context['graph'])
    graph = Graph(logger, graph_dict["trace_id"])
    graph.organizeId = context['organizeId']
    graph.subtaskId = context['subtaskId']
    result = graph.execute_task_call(context['subtaskId'], context['taskId'], graph_dict, network, context['vertex'], context["parameterList"], context['organizeId'])
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
