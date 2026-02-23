import sys
import os

def get_app_path(filename):
    """获取应用程序所在目录的文件路径"""
    if getattr(sys, 'frozen', False):  # 打包后的环境
        app_dir = os.path.dirname(sys.executable)
    else:  # 开发环境
        # core/utils.py -> project/core/utils.py
        # dirname(abspath(__file__)) -> project/core
        # dirname(...) -> project
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(app_dir, filename)
