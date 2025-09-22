import logging
import os
import signal
import sys
import threading
import time
import traceback

from utils.log_utils import init_root_logger

init_root_logger("fastapi-template")
from utils import file_utils
from config import settings, show_configs

stop_event = threading.Event()

RAGFLOW_DEBUGPY_LISTEN = int(os.environ.get('RAGFLOW_DEBUGPY_LISTEN', "0"))


def signal_handler(sig, frame):
    logging.info("Received interrupt signal, shutting down...")
    stop_event.set()
    time.sleep(1)
    sys.exit(0)


if __name__ == '__main__':

    logging.info(
        f'project base: {file_utils.get_project_base_directory()}'
    )
    show_configs()
    # import argparse
    # parser = argparse.ArgumentParser()
    #
    # args = parser.parse_args()
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    try:
        logging.info("服务启动ing...")
        logging.info(r"""
        ______              _     ___  ______  _____          _____                          _         _         
        |  ___|            | |   / _ \ | ___ \|_   _|        |_   _|                        | |       | |        
        | |_     __ _  ___ | |_ / /_\ \| |_/ /  | |   ______   | |    ___  _ __ ___   _ __  | |  __ _ | |_   ___ 
        |  _|   / _` |/ __|| __||  _  ||  __/   | |  |______|  | |   / _ \| '_ ` _ \ | '_ \ | | / _` || __| / _ \
        | |    | (_| |\__ \| |_ | | | || |     _| |_           | |  |  __/| | | | | || |_) || || (_| || |_ |  __/
        \_|     \__,_||___/ \__|\_| |_/\_|     \___/           \_/   \___||_| |_| |_|| .__/ |_| \__,_| \__| \___|
                                                                                     | |                         
                                                                                     |_|                         
            """)

        import uvicorn

        # 配置Uvicorn参数
        uvicorn_config = {
            # "app": app,  # FastAPI应用实例
            "app": "config.fastapi_config:app",  # FastAPI应用实例
            "host": settings.host_ip,
            "port": settings.host_port,
            "reload": settings.debug,  # 开发模式启用热重载
            "log_level": "debug" if settings.debug else "info",
            "access_log": True,
        }
        # 如果是调试模式，添加额外配置
        if settings.debug:
            uvicorn_config.update({
                "reload_dirs": ["."],  # 监视当前目录变化
                "reload_delay": 0.5,  # 重载延迟
            })

        # 启动Uvicorn服务器
        uvicorn.run(**uvicorn_config)
    except Exception:
        traceback.print_exc()
        stop_event.set()
        time.sleep(1)
        os.kill(os.getpid(), signal.SIGKILL)
