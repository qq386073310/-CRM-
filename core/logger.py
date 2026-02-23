import sys
import os
import logging
import traceback
from logging.handlers import RotatingFileHandler
from datetime import datetime
from PyQt5.QtWidgets import QMessageBox

# 确保日志目录存在
LOG_DIR = os.path.join(os.getcwd(), 'logs')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FILE = os.path.join(LOG_DIR, 'app.log')

def setup_logger():
    """配置全局日志"""
    logger = logging.getLogger('CustomerManager')
    logger.setLevel(logging.DEBUG)
    
    # 防止重复添加handler
    if logger.handlers:
        return logger
        
    # 文件处理器 (按大小轮转，最大5MB，保留5个备份)
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# 初始化全局logger
logger = setup_logger()

def install_exception_hook():
    """安装全局异常捕获钩子"""
    sys.excepthook = exception_hook

def exception_hook(exc_type, exc_value, exc_traceback):
    """全局异常处理函数"""
    # 忽略键盘中断 (Ctrl+C)
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    # 获取详细的错误堆栈
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    
    # 记录到日志
    logger.critical(f"Uncaught exception:\n{error_msg}")
    
    # 尝试弹窗提示用户 (如果在GUI线程中)
    try:
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            # 避免在错误循环中无限弹窗
            # 这里简单处理，直接弹窗
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle("程序发生严重错误")
            msg_box.setText("程序发生未预料的错误，可能需要重启。")
            msg_box.setInformativeText(f"错误信息已记录到日志文件。\n\n错误类型: {exc_type.__name__}\n错误描述: {str(exc_value)}")
            msg_box.setDetailedText(error_msg)
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec_()
    except Exception as e:
        # 如果弹窗也失败了（比如Qt还没初始化），至少打印到控制台
        logger.critical(f"Failed to show error dialog: {e}")

