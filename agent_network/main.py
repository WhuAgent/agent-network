import threading
from posix import _exit

from agent_network.network.route import Route
from agent_network.pipeline.pipeline import Pipeline
from agent_network.pipeline.task import TaskNode
from agent_network.utils.logger import Logger
from flask import Flask, request
from agent_network.network.graph import GraphStart, Graph
from agent_network.network.network import Network

app = Flask(__name__)
network = Network('agent-network', None, None, None)


@app.route('/task', methods=['GET'])
def task():
    graph = request.args.get('graph')
    current_task = request.args.get('task')
    config_dir = request.args.get('dir')
    # config_dir = "agent_network/config"
    logger = Logger("log")
    pipeline = Pipeline(current_task, config_dir, logger)
    pipeline.execute(network.get_graph(graph), Route(), [TaskNode(pipeline.config["start_node"], current_task)])
    result = pipeline.retrieve_results()
    pipeline.release()
    return result


def run_web(debug=False):
    app.run(host='0.0.0.0', port=18080, debug=debug)


if __name__ == '__main__':
    web_thread = threading.Thread(target=run_web)
    web_thread.start()
    graph = Graph('graph', None, None, None, None, None)
    # graph_start = GraphStart(graph)
    network.add_graph(graph.name, graph)
    input("Press Enter to shutdown the agent network...\n")
    _exit(0)
