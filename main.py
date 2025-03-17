from agent_network.graph.graph import Graph
import uasyncio as asyncio
from microdot import Microdot, Response
from agent_network.constant import network, logger

app = Microdot()
Response.default_content_type = "application/json"

import sys
sys.path.append('/')

@app.post('/service')
async def service(request):
    context = request.json
    if not context or 'flowId' not in context or 'task' not in context:
        return {"error": "缺少必要的参数 flowId 或 task"}, 400
    graph = Graph(logger)
    graph.execute(network, context['flowId'], context['params'])
    result = graph.retrieve_results()
    graph.release()
    return result


async def run_web(debug=False):
    app.run(host='0.0.0.0', port=18080, debug=debug)


if __name__ == '__main__':
    asyncio.run(run_web())
    while True:
        pass
