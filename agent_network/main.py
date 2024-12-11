import threading
from posix import _exit
from pipeline.pipeline import Pipeline
from utils.logger import Logger
from flask import Flask, request
from network.graph import GraphStart, Graph
from network.network import Network

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
    pipeline.execute(network.get_graph(graph))
    result = pipeline.retrieve_results()
    pipeline.release()
    return result


def run_web(debug=False):
    app.run(host='0.0.0.0', port=18080, debug=debug)


if __name__ == '__main__':
    web_thread = threading.Thread(target=run_web)
    web_thread.start()
    graph = Graph('graph', None, None, None)
    graph_start = GraphStart(graph)
    network.add_graph(graph.name, graph_start)
    input("Press Enter to shutdown the agent network...\n")
    _exit(0)
