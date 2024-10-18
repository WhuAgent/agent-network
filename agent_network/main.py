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
    pipeline = Pipeline(config_dir, logger)
    pipeline.agent(network.get_graph(graph), current_task)
    result = pipeline.retrieve_results()
    pipeline.release()
    return result


def run_web(debug=False):
    app.run(host='0.0.0.0', port=18080, debug=debug)


if __name__ == '__main__':
    run_web()
    graph = Graph('graph', None, None, None)
    graph_start = GraphStart(graph)
    network.add_graph(graph.name, graph_start)
    # pipeline.forward(task)
