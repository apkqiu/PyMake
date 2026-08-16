import os
import subprocess
import threading
from collections.abc import Iterable

from .logger import LOGDIR, getLogger


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


def execute(
    *cmdline,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    check=True,
    capture=False,
):
    global id
    with id_lock:
        id += 1
        lid = id
    logger = getLogger("ShellExecute")
    cmd = parse_cmd(cmdline)
    log_out_name = os.path.join(LOGDIR, f"run-{lid}-stdout.log")
    log_err_name = os.path.join(LOGDIR, f"run-{lid}-stderr.log")

    logger.info(f"Executing {cmd!r} (Run {lid})")

    with open(log_out_name, "w") as log_out, open(log_err_name, "w") as log_err:
        code = subprocess.call(
            cmd,
            env=env,
            cwd=cwd,
            stdout=log_out.fileno(),
            stderr=log_err.fileno(),
        )

    if check and code:
        logger.error(f"Process (Run {lid}) exited with exit code {code}")
        raise ChildProcessError(f"Process (Run {lid}) exited with exit code {code}")
    logger.info(f"Process (Run {lid}) exited with exit code {code}")
    if capture:
        return open(log_out_name, "r").read()
