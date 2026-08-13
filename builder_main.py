import argparse
import concurrent.futures
import os
import sys
import traceback
from collections.abc import Callable
from logging import getLevelNamesMapping
from typing import Any

from .logger import getLogger, verbose
from .make_config import MakeConfig
from .make_factory import Dispatcher, MakeFactory


class ThreadPoolDispatcher(Dispatcher):
    def __init__(self):
        self.pool = concurrent.futures.ThreadPoolExecutor(8)
    
    def begin(self, func: Callable, *args, **kwargs) -> Any:
        return self.pool.submit(func, *args, **kwargs)
    def end(self, id: Any):
        concurrent.futures.wait([id])
        return id.exception() is None


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("-V", "--version", action="version", version="%(prog)s 0.2")
    parser.add_argument("-c", "--command", action="store", help="run command.")
    parser.add_argument(
        "-t",
        "--target",
        action="store",
        help="set build target. Default is defined in your meta file",
    )
    parser.add_argument(
        "-f", "--meta-file", action="store", help="set meta file. Default is 'make.py'"
    )
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="list targets or commands. use -tl to list targets, -cl to list commands.",
    )
    parser.add_argument(
        "-v",
        "--log-level",
        choices=getLevelNamesMapping().keys(),
        help="set log level.",
    )
    # logging.basicConfig(
    #     level=logging.DEBUG,
    # )
    args = parser.parse_args()
    if args.log_level:
        verbose(getLevelNamesMapping()[args.log_level])
    logger = getLogger("Exit")
    try:

        cfg = MakeConfig()
        if args.meta_file:
            cfg.include(args.meta_file)
        else:
            cfg.subdir(os.getcwd())
        factory = MakeFactory(cfg, ThreadPoolDispatcher())


        if args.command:
            if args.list:
                for i in cfg.commands:
                    print(i)
            else:
                factory.call_command(args.command)
        else:
            if args.list:
                for i, j in cfg.rules.items():
                    print(i)
                    if i == cfg.default:
                        print("| > Default")
                    if len(j[0]) > 0:
                        print("| > Requires:", j[0][0])
                        for i in range(1, len(j[0])):
                            print("|            ", j[0][i])
                    print()
            else:
                factory.build(args.target or cfg.default)

    except BaseException as e:
        for i in "".join(traceback.format_exception(e)).splitlines():
            logger.critical(i)
        sys.exit(1)


if __name__ == "__main__":
    main()
