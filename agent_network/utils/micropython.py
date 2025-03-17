import uos


def path_join(*args):
    return "/".join(args)  # MicroPython 只支持 POSIX 路径


def path_exists(path):
    try:
        uos.stat(path)  # 如果文件/目录存在，则不会报错
        return True
    except OSError:
        return False


def make_dirs(path):
    """递归创建目录（MicroPython 没有 os.makedirs）"""
    dirs = path.split("/")
    current_path = ""
    for d in dirs:
        if d:  # 忽略空字符串
            current_path = current_path + "/" + d
            try:
                uos.mkdir(current_path)
            except OSError:
                pass  # 目录已存在时忽略错误
