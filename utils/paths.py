import sys
import os

def get_app_path(filename):
    """获取应用程序所在目录的文件路径(用于可写文件)"""
    if getattr(sys, 'frozen', False):
        app_dir = os.path.dirname(sys.executable)
    else:
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(app_dir, filename)

def get_resource_path(relative_path):
    """获取资源文件路径(支持PyInstaller打包)"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return get_app_path(relative_path)
