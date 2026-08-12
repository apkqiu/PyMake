import argparse
import concurrent.futures
from logging import getLevelNamesMapping
import os
import sys
import time
import traceback

from .config import MakeConfig
from .logger import getLogger, verbose
from .util import make_queue, need_build, place_data


def make(cfg: MakeConfig, target: str):
    start = time.time()

    pool = concurrent.futures.ThreadPoolExecutor(16, thread_name_prefix="MakeWorker")
    logger = getLogger("PyMake")
    built_objs = set()

    has_built = False
    stop = False

    def do_task(prod, req, call):
        nonlocal has_built
        while not all(r in built_objs for r in req):
            if stop:
                return
        if need_build(prod, req):
            has_built = True
            logger.info(f"Building {prod} << {req}")
            call()
        else:
            logger.info(f"Skipped {prod}")
        built_objs.add(prod)

    fs: list[concurrent.futures.Future] = []
    for prod, req, call in make_queue(cfg, target):
        for r in req:
            if os.path.exists(r) and r not in cfg.tasks:
                built_objs.add(r)
        os.makedirs(os.path.abspath(os.path.split(prod)[0]), exist_ok=True)
        f = pool.submit(do_task, prod, req, call)
        fs.append(f)

    done, not_done = concurrent.futures.wait(
        fs, return_when=concurrent.futures.FIRST_EXCEPTION
    )
    fs = not_done
    for i in done:
        e = i.exception()
        if e:
            pool.shutdown(wait=False)
            raise e
    pool.shutdown(wait=True)
    if not has_built:
        logger.warning("Noting to do.")
    place_data(target, {"target": True})
    logger.info(f"Compilation completed. Took {time.time() - start:.1f} seconds.")


def command(cfg: MakeConfig, cmd: str):
    cfg.commands[cmd]()


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
        cfg = MakeConfig(root_check=False)
        if args.meta_file:
            cfg.include(args.meta_file)
        else:
            cfg.subdir(os.getcwd())
        if args.command:
            if args.list:
                for i in cfg.commands:
                    print(i)
            else:
                command(cfg, args.command)
        else:
            if args.list:
                for i, j in cfg.tasks.items():
                    print(i)
                    if i == cfg.default:
                        print("| > Default")
                    if len(j[0]) > 0:
                        print("| > Requires:", j[0][0])
                        for i in range(1, len(j[0])):
                            print("|            ", j[0][i])
                    print()
            else:
                make(cfg, args.target or cfg.default)
    except ChildProcessError:
        sys.exit(1)
    except BaseException as e:
        for i in "".join(traceback.format_exception(e)).splitlines():
            logger.critical(i)
        sys.exit(1)


if __name__ == "__main__":
    main()
