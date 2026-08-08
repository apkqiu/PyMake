import logging

import colorlog

LEVEL = logging.INFO

def verbose(level):
    global LEVEL
    LEVEL = level

def getLogger(name: str):
    
    # 创建logger对象
    logger = logging.getLogger(name)
    logger.setLevel(LEVEL)
    # 创建控制台日志处理器
    console_handler = logging.StreamHandler()
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
    # 移除默认的handler
    for handler in logger.handlers:
        logger.removeHandler(handler)
    # 将控制台日志处理器添加到logger对象
    logger.addHandler(console_handler)
    return logger