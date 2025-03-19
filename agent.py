from agent_network.base import BaseAgent
from agent_network.exceptions import ReportError


class worker(BaseAgent):
    def __init__(self, graph, config, logger):
        super().__init__(graph, config, logger)
        
    def forward(self, messages, **kwargs):
        if error_message := kwargs.get("graph_error_message"):
            prompt = f"错误：{error_message}"
        else:
            task = kwargs.get("task")
            prompt = task
            
            if ocr_result :=  kwargs.get("ocr_result"):
                prompt += f"\n\n相关文件的文字识别结果为 {ocr_result}"
                
        self.add_message("user", prompt, messages)
        response = self.chat_llm(messages,
                                 api_key="sk-ca3583e3026949299186dcbf3fc34f8c",
                                 base_url="https://api.deepseek.com",
                                 model="deepseek-chat",
                                 response_format={"type": "json_object"})
        
        response_data = response.content
        
        if "tool_name" in response_data:
            result = {
                "next_executors": [response_data["tool_name"]],
                **response_data["tool_args"]
                }
            return result
        elif "result" in response_data:
            result = {
                "result": response_data["result"]
            }
            return result
        else:
            raise ReportError("unknown response format", "worker")
    

class ocr_tool(BaseAgent):
    def __init__(self, graph, config, logger):
        super().__init__(graph, config, logger)
        
    def forward(self, messages, **kwargs):
        ocr_file_name = kwargs.get("ocr_file_path")
        if not ocr_file_name:
            raise ReportError("ocr_file_path is not provided", "worker")
        
        import easyocr
        reader = easyocr.Reader(['ch_sim','en'])
        ocr_result = reader.readtext(ocr_file_name, detail=0)
        self.log("assistant", ocr_result)
        
        result = {
            "ocr_result": ocr_result
        }
        return result