import atexit
import glob as _glob
import hashlib
import json
import os
import queue
import typing
from functools import partial

from .logger import getLogger

if typing.TYPE_CHECKING:
    from .config import MakeConfig


def glob(pattern: str):
    return _glob.iglob(pattern, recursive=True)


hashes = {}
new_hashes = {}
if os.path.exists(".cache.json"):
    hashes = json.load(open(".cache.json"))




def make_queue(config: "MakeConfig", target: str):
    logger = getLogger("QueueBuilder")
    state = {}          # 0=未访问, 1=正在处理（路径中）, 2=已处理
    stack = [[target, 0]]   # [目标, 下一个要处理的依赖索引]
    path = []           # 用于循环检测

    while stack:
        t, idx = stack[-1]   # 查看栈顶（不弹出）

        # 如果该节点尚未标记状态，标记为正在处理
        if state.get(t, 0) == 0:
            logger.debug(f"Enter {t}")
            state[t] = 1
            path.append(t)

        # 检查节点是否可构建
        if t not in config.tasks:
            if os.path.exists(t):
                logger.debug(f"No build - {t}")
                state[t] = 2
                path.pop()
                stack.pop()
                continue
            else:
                raise ValueError(f"Cannot build {t}")

        req, func = config.tasks[t]

        # 跳过已经处理的依赖（状态2）或头文件
        while idx < len(req):
            dep = req[idx]
            dep_state = state.get(dep, 0)
            if dep_state == 1:
                # 循环检测
                cycle = path[path.index(dep):] + [dep]
                raise ValueError(f"Circular dependency: {' -> '.join(cycle)}")
            if dep_state == 2:
                # 依赖已处理，跳过
                logger.debug(f"Skipped {dep} (already processed)")
                idx += 1
                stack[-1][1] = idx
                continue
            # 否则，需要处理该依赖
            break

        # 如果所有依赖都已处理（包括跳过）
        if idx == len(req):
            logger.debug(f"Leave {t}")
            yield (t, req, partial(func, t, req))
            state[t] = 2
            path.pop()
            stack.pop()
            continue

        # 处理当前未处理的依赖
        dep = req[idx]
        logger.debug(f"Prepare {t} -> {dep}")
        stack[-1][1] = idx + 1          # 更新当前节点索引，以便返回时继续
        stack.append([dep, 0])          # 压入依赖



def calchash(f):
    fd = open(f, "rb")
    buf = bytearray(0 for i in range(8192))
    obj = hashlib.md5()
    while True:
        c = fd.readinto(buf)
        obj.update(buf[:c])
        if c < 1024:
            return obj.hexdigest()


def need_build(target, dependencies):
    # 无论如何都要跑一遍哈希
    logger = getLogger("hash")
    result = False
    for dep in dependencies:
        new = {
            "hash": calchash(dep)
        }
        old = place_data(dep, new)
        if new["hash"] != old.get("hash"):
            logger.debug(f"Hash Mismatch {dep}: {old.get('hash')} -- {new["hash"]}")
            result = True
    if not os.path.exists(target):
        return True
    if result:
        return True
    return target not in hashes

def place_data(key:str, value:dict | None=None):
    if value:
        if key not in new_hashes:
            new_hashes[key] = {}
        new_hashes[key].update(value)
    return hashes.get(key, {})

@atexit.register
def dump_hashes():
    if len(new_hashes):
        json.dump(new_hashes, open(".cache.json", "w"), indent=4)


def n(name: str):
    r = name.rfind(".")
    if r == -1:
        r = len(name)
    l = name.find("/") + 1
    return name[l:r]
