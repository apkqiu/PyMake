import os
import subprocess
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


def execute(*cmdline, env:dict[str, str]|None=None, check=True, log=True):
    logger = getLogger("ShellExecute", not log)
    out_logger = getLogger("ShellExecute_tty", not log)
    cmd = parse_cmd(cmdline)
    logger.info(f"Executing \033[33m'{"' '".join(cmd)}'\033[0m")
    r1, w1 = os.pipe2(os.O_NONBLOCK)
    r2, w2 = os.pipe2(os.O_NONBLOCK)
    p = subprocess.Popen(cmd, stdout=w1, stderr=w2, env=env)
    stdout = open(r1, "rb")
    stderr = open(r2, "rb")
    prev_outbuf = b""
    prev_errbuf = b""
    outbuf = b""
    errbuf = b""
    while p.poll() is None:
        c = stdout.read(1)
        if c:
            outbuf += c
            if outbuf.endswith(b"\n"):
                out_logger.info(outbuf.decode().strip())
                outbuf = b""
        else:
            if outbuf != prev_outbuf:
                prev_outbuf = outbuf
                out_logger.info(outbuf.decode().strip() + "<?>")

        c = stderr.read(1)
        if c:
            errbuf += c
            if errbuf.endswith(b"\n"):
                out_logger.error(errbuf.decode().strip())
                errbuf = b""
        else:
            if errbuf != prev_errbuf:
                prev_errbuf = errbuf
                out_logger.error(errbuf.decode().strip() + "<?>")
    while True:
        c = stdout.read(1)
        if c:
            outbuf += c
            if outbuf.endswith(b"\n"):
                out_logger.info(outbuf.decode().strip())
                outbuf = b""
        else:
            break
    while True:
        c = stderr.read(1)
        if c:
            errbuf += c
            if errbuf.endswith(b"\n"):
                out_logger.error(errbuf.decode().strip())
                errbuf = b""
        else:
            break
    code = p.poll()
    if check and code:
        logger.error(f"Process exited with exit code {code}")
        raise ChildProcessError(f"Process exited with exit code {code}")
    logger.info(f"Process exited with exit code {code}")


def execute_capture(*cmdline, env:dict[str, str]|None=None, check=True, log=True):
    logger = getLogger("ShellExecute", not log)
    out_logger = getLogger("ShellExecute_tty", not log)
    cmd = parse_cmd(cmdline)
    logger.info(
        f"Executing \033[33m'{"' '".join(cmd)}'\033[0m - Output has been captured."
    )
    try:
        out = subprocess.check_output(cmd, encoding="utf-8", env=env)
        for line in out.splitlines():
            out_logger.info(line)
    except subprocess.CalledProcessError as e:
        if check:
            logger.error(f"Process exited with exit code {e.returncode}")
            raise ChildProcessError(f"Process exited with exit code {e.returncode}")
        logger.info(f"Process exited with exit code {e.returncode}")
    else:
        logger.info("Process exited with exit code 0")
    return out
