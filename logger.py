import datetime
import logging
import os

import colorlog

LEVEL = logging.INFO

def verbose(level):
    global LEVEL
    LEVEL = level

def getLogger(name: str, dummy=False):
    # 创建logger对象
    logger = logging.getLogger(name)
    logger.setLevel(LEVEL)
    logger.propagate = False
    # 创建控制台日志处理器
    console_handler = logging.StreamHandler()
    if dummy:
        console_handler.setLevel(999999)
    else:
        console_handler.setLevel(LEVEL)
    # 定义颜色输出格式
    color_formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(processName)s - %(threadName)s - %(name)s [%(levelname)s]%(reset)s %(message)s",
        log_colors={
            "DEBUG": "bold_purple",
            "INFO": "bold_blue",
            "WARNING": "bold_yellow",
            "ERROR": "bold_red",
            "CRITICAL": "white,bg_red",
        },
    )
    # 将颜色输出格式添加到控制台日志处理器
    console_handler.setFormatter(color_formatter)

    file_handler = logging.FileHandler(os.path.join(LOGDIR, f"pylog-{name}.log"))
    file_handler.setLevel(20)

    normal_formatter = logging.Formatter("%(processName)s - %(threadName)s - %(name)s [%(levelname)s] %(message)s")
    file_handler.setFormatter(normal_formatter)

    # 移除默认的handler
    logger.handlers.clear()
    # 将控制台日志处理器添加到logger对象
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger

LOGDIR = os.path.join("logs", datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f"))
os.makedirs(LOGDIR, exist_ok=True)

o = sorted(os.listdir("logs"), reverse=True)
for i in o[4:]:
    import shutil
    shutil.rmtree(os.path.join("logs", i))