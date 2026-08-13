import hashlib
import copy
import json
import os
from collections import defaultdict
from collections.abc import Callable, Generator
from typing import Any

from .make_config import MakeConfig, Rule


class Dispatcher:
    # 开始，不保证立即开始
    def begin(self, func: Callable, *args, **kwargs) -> Any: ...
    # 结束，保证等待结束，返回是否成功
    def end(self, id: Any) -> bool: ...


class SimpleDispatcher(Dispatcher):
    def begin(self, func: Callable, *args, **kwargs) -> int:
        func(*args, **kwargs)
        return 0

    def end(self, id: int):
        return True  # always complete


BUFSIZE = 8192


def calchash(f):
    with open(f, "rb") as fd:
        obj = hashlib.blake2b()
        while True:
            buf = fd.read(BUFSIZE)
            obj.update(buf)
            if not buf:
                return obj.hexdigest()
def objhash(buf:bytes):
    obj = hashlib.blake2b()
    obj.update(buf)
    return obj.hexdigest()

class MakeFactory:
    def __init__(self, config: MakeConfig, dispatcher: Dispatcher):
        self.config = config
        self.dispatcher = dispatcher

    def yield_queue(self, target: str, parent: str | None = None) -> Generator[Rule]:
        rule = self.config.rules.get(target)
        if rule is None:
            if not os.path.exists(target):
                raise FileNotFoundError(
                    f"{target} not found, and it cannot be built. Required by {parent}"
                )
            else:
                return
        for r in rule.dependencies:
            yield from self.yield_queue(r, target)
        yield rule

    def __load_cache(self):
        """加载旧缓存，若文件损坏则返回空defaultdict"""
        if not os.path.exists(".cache.json"):
            return defaultdict(dict)
        try:
            d = defaultdict(dict)
            with open(".cache.json") as f:
                data = json.load(f)
            d.update(data)
            # 将普通dict转为defaultdict结构
            return d
        except json.JSONDecodeError:
            return defaultdict(dict)

    def __save_cache(self, data) -> None:
        """将新缓存写入文件"""
        # 将defaultdict转为普通dict以便json序列化
        to_dump = {k: dict(v) for k, v in data.items()}
        with open(".cache.json", "w") as f:
            json.dump(to_dump, f, indent=4)


    def __prepare(self, rule: Rule, data:dict[str, dict]):
        target = rule.product
        target = os.path.normpath(target)
        target_d = os.path.dirname(target)
        if target_d and not os.path.exists(target_d):
            os.makedirs(target_d, exist_ok=True)


        deps = {}
        rebuild = False
        if rule.dependencies:
            deps["$"+objhash(rule.build_func.__code__.co_code)] = rule.dependencies
        if os.path.exists(target):
            current_hash = calchash(target)
            if current_hash != data[target].get("hash"):
                rebuild = True
                data[target]["hash"] = current_hash

                for trace in rule.tracers:
                    deps[objhash(trace.__code__.co_code)] = sorted(os.path.normpath(i) for i in trace(target))
        else:
            rebuild = True

        if data[target].get("dependencies") != deps:
            rebuild = True
            data[target]["dependencies"] = deps


        all_deps = []
        for i in deps.values():
            all_deps.extend(os.path.normpath(j) for j in i)
        all_deps = sorted({*all_deps}) # 处理一些奇奇怪怪的情况

        return rebuild, all_deps

    def __wait_deps(self, deps: list, status: dict, data:dict[str, dict]):
        rebuild = False
        for dep in deps:
            dep = os.path.normpath(dep)
            id = status.get(dep)
            if id:
                if not self.dispatcher.end(id):
                    return None, False
            elif not os.path.exists(dep):
                # 假阳性？
                return None, False
            current_hash = calchash(dep)
            if current_hash != data[dep].get("hash"):
                rebuild = True
                data[dep]["hash"] = current_hash
        return rebuild, True
    
    def build(self, target: str):

        data = self.__load_cache()
        status = {}
        for rule in self.yield_queue(target):
            rebuild, all_deps = self.__prepare(rule, data)
            deps_rebuilt, cont = self.__wait_deps(all_deps, status, data)
            if not cont:
                return False
            if rebuild or deps_rebuilt:
                status[rule.product] = self.dispatcher.begin(
                    rule.build_func, rule.product, rule.dependencies
                )
        ti = status.get(target)
        if ti:
            self.dispatcher.end(ti)

        self.__save_cache(data)
        return True
    def call_command(self, name: str):
        id = self.dispatcher.begin(self.config.commands[name])
        return self.dispatcher.end(id)
