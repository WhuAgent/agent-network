import json
import time
import agent_network.utils.micropython as mp
import uos

class Logger:
    def __init__(self, root, prefix="", global_switch=True):
        self.start_time = str(time.time())
        self.dir_name = f"{prefix}-{self.start_time}" if prefix else self.start_time
        self.log_dir = mp.path_join(root, self.dir_name)
        if not mp.path_exists(self.log_dir):
            mp.make_dirs(self.log_dir)
        self.root = root
        self.prefix = prefix
        self.all_log_file_name = "all.log"
        self.all_log_file_path = mp.path_join(self.log_dir, self.all_log_file_name)
        self.trace_log_file_name = "trace.log"
        self.trace_log_file_path = mp.path_join(self.log_dir, self.trace_log_file_name)
        self.global_switch = global_switch
        self.message_history = []

    def log_trace(self, trace):
        if self.global_switch:
            with open(self.trace_log_file_path, 'a', encoding="UTF-8") as f:
                f.write(repr(trace))

    def log(self, role="", content="", instance="", output=True, cur_time=None):
        """
        params:
            role: 消息的类型，分为 network, system, user, assistant(opanai)
            content: 消息的内容
            instance: 产生消息的实体名称
            output: 是否输出到控制台
            cur_time: 产生消息的时间
        """
        if cur_time is None:
            cur_time = time.time()
        if not isinstance(content, str):
            content = json.dumps(content, indent=4, ensure_ascii=False)
        buffer = "---------------------------------------------------\n"
        buffer += f"[{cur_time}]"
        if instance:
            buffer += f"[{instance}]"
        if role:
            buffer += f"[{role}]"
        buffer += f"\n{content}\n\n"

        if output:
            print(buffer)
        if self.global_switch:
            with open(self.all_log_file_path, 'a', encoding="UTF-8") as f:
                f.write(buffer)

        self.message_history.append(
            {
                "role": role,
                "content": content,
                "instance": instance,
                "time": cur_time
            }
        )

    def categorize_log(self):
        vis_data_path = mp.path_join(self.log_dir, "vis_data.json")
        if self.global_switch:
            with open(vis_data_path, "w", encoding="UTF-8") as f:
                f.write(json.dumps(self.message_history, indent=4, ensure_ascii=False))

        for message in self.message_history:
            file_path = mp.path_join(self.log_dir, f"{message['instance']}.log")
            if self.global_switch:
                with open(file_path, "a", encoding="UTF-8") as f:
                    buffer = "---------------------------------------------------\n"
                    buffer += f"[{message['time']}][{message['instance']}][{message['role']}]\n"
                    buffer += f"{message['content']}\n\n"
                    f.write(buffer)

    def rename(self, success):
        file_name, extension = self.file_name.split(".")
        success = 'success' if success else 'fail'
        new_file_name = f"{file_name}-{success}.{extension}"
        new_file_path = mp.path_join(self.root, new_file_name)
        uos.rename(self.file_path, new_file_path)
        self.file_name = new_file_name
        self.file_path = new_file_path

    def set_prefix(self, prefix):
        self.prefix = prefix
        self.file_name = f"{prefix}.txt" if prefix else f"{self.start_time}.txt"
        self.file_path = mp.path_join(self.log_dir, self.file_name)
