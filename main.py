import threading

from agent_network.graph.graph import Graph
from flask import Flask, request
from agent_network.constant import network, logger

app = Flask(__name__)


@app.route('/service', methods=['POST'])
def service():
    context = request.json
    
    assert context['task'] is not None, "智能体任务未找到"
    
    graph = Graph(logger)
    
    if flow_id := context.get("flowId"):
        result = graph.execute(network, context["task"], start_vertex=flow_id, params=context.get("params", {}), results=context.get("results", {}))
    else:
        result = graph.execute(network, context["task"], params=context.get("params", {}), results=context.get("results", {}))
    
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
    "task": "学校发了一个新的讲座通知，相关文件已给出，能告诉我讲座什么时候在哪里举行，是有关于什么的讲座吗？",
    "params": {
        "file_path": "C:\\Users\\lornd\\Downloads\\FC804E96CF497636909FC43BE21_07186CAC_E21D4.jpg",
    }
}
"""
