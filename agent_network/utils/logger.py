import json
import os
from datetime import datetime


class Logger:
    def __init__(self, root, prefix=""):
        self.start_time = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.dir_name = f"{prefix}-{self.start_time}" if prefix else self.start_time
        self.log_dir = os.path.join(root, self.dir_name)
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        self.root = root
        self.prefix = prefix
        self.file_name = f"{prefix}-{self.start_time}.txt" if prefix else f"{self.start_time}.txt"
        self.file_path = os.path.join(self.log_dir, self.file_name)

    def log(self, content):
        if not isinstance(content, str):
            content = json.dumps(content, indent=4, ensure_ascii=False)
        with open(self.file_path, 'a', encoding="UTF-8") as f:
            f.write(content)
            f.write("\n")
            f.write("\n")

    def rename(self, success):
        file_name, extension = self.file_name.split(".")
        success = 'success' if success else 'fail'
        new_file_name = f"{file_name}-{success}.{extension}"
        new_file_path = os.path.join(self.root, new_file_name)
        os.rename(self.file_path, new_file_path)
        self.file_name = new_file_name
        self.file_path = new_file_path

    def set_prefix(self, prefix):
        self.prefix = prefix
        self.file_name = f"{prefix}.txt" if prefix else f"{self.start_time}.txt"
        self.file_path = os.path.join(self.log_dir, self.file_name)
