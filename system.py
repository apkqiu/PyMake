from datetime import datetime
import os
import shutil
import subprocess
import threading
from collections.abc import Iterable

from .logger import getLogger


def parse_cmd(cmdline):
    cmd = []
    for i in cmdline:
        if isinstance(i, str):
            cmd.append(i)
        elif isinstance(i, Iterable):
            cmd.extend(parse_cmd(i))
        else:
            cmd.append(str(i))
    return cmd


id = 0
id_lock = threading.Lock()
LOGDIR = os.path.join("logs",datetime.now().strftime("%Y%m%d_%H%M%S_%f"))
os.makedirs(LOGDIR, exist_ok=True)


def execute(
    *cmdline, cwd: str | None = None, env: dict[str, str] | None = None, check=True
):
    logger = getLogger("ShellExecute")
    cmd = parse_cmd(cmdline)
    lid = 0
    with id_lock:
        global id
        id += 1
        lid = id
    log_out_name = os.path.join(LOGDIR, f"run-{lid}-stdout.log")
    log_err_name = os.path.join(LOGDIR, f"run-{lid}-stderr.log")

    logger.info(f"Executing \033[33m'{"' '".join(cmd)}'\033[0m (Run {lid})")

    with open(log_out_name, "w") as log_out, open(log_err_name, "w") as log_err:
        log_out.write(f"Command: {cmd!r}\n\n") # 使用repr消歧义
        log_err.write(f"Command: {cmd!r}\n\n")

        log_out.flush()
        log_err.flush()
        code = subprocess.call(
            cmd,
            env=env,
            cwd=cwd,
            stdout=log_out.fileno(),
            stderr=log_err.fileno(),
        )

        # 由于stderr不常用，可以放一些统计性的东西：

        log_err.write(f"""------------------------------------
Exit Code: {code}""")
        log_err.flush()

    if check and code:
        logger.error(f"Process (Run {lid}) exited with exit code {code}")
        raise ChildProcessError(f"Process (Run {lid}) exited with exit code {code}")
    logger.info(f"Process (Run {lid}) exited with exit code {code}")


def execute_capture(
    *cmdline,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    check=True,
    log=True,
):
    logger = getLogger("ShellExecute", not log)
    cmd = parse_cmd(cmdline)
    logger.info(
        f"Executing \033[33m'{"' '".join(cmd)}'\033[0m - Output has been captured."
    )
    try:
        out = subprocess.check_output(cmd, encoding="utf-8", env=env, cwd=cwd)
    except subprocess.CalledProcessError as e:
        if check:
            logger.error(f"Process exited with exit code {e.returncode}")
            raise ChildProcessError(f"Process exited with exit code {e.returncode}")
        logger.info(f"Process exited with exit code {e.returncode}")
    else:
        logger.info("Process exited with exit code 0")
    return out
