import hashlib
import json
import os
from collections.abc import Callable, Generator
from functools import lru_cache, cache

from ..utils.logger import getLogger
from .dispatcher import Dispatcher
from .make_config import MakeConfig, Rule

BUFSIZE = 1 * 1024 * 1024

@lru_cache(128)
def _calchash(f, k):
    with open(f, "rb") as fd:
        obj = hashlib.blake2b()
        while True:
            buf = fd.read(BUFSIZE)
            obj.update(buf)
            if len(buf) != BUFSIZE:
                return obj.hexdigest()

def calchash(f):
    st = os.stat(f)
    return _calchash(f, (st.st_size, st.st_mtime))

@cache
def funhash(obj: Callable):
    bytecode = obj.__code__.co_code
    hash = hashlib.blake2b()
    hash.update(bytecode)
    return hash.hexdigest()


class MakeFactory:
    def __init__(self, config: MakeConfig, dispatcher: Dispatcher):
        self.config = config
        self.dispatcher = dispatcher
        self.data = self.__load_cache()

    def yield_queue(
        self, target: str, parent: str | None = None, visited: set | None = None
    ) -> Generator[Rule]:
        if visited is None:
            visited = set()
        if target in visited:
            return
        visited.add(target)
        rule = self.config.rules.get(target)
        if rule is None:
            if not os.path.exists(target):
                raise FileNotFoundError(
                    f"{target} not found, and it cannot be built. Required by {parent}"
                )
            else:
                return

        for r in rule.dependencies:
            yield from self.yield_queue(r, target, visited)
        yield rule

    def __load_cache(self):
        """加载旧缓存，若文件损坏则返回空defaultdict"""
        if not os.path.exists(".cache.json"):
            return {}
        try:
            d = {}
            with open(".cache.json") as f:
                data = json.load(f)
            d.update(data)
            # 将普通dict转为defaultdict结构
            return d
        except json.JSONDecodeError:
            return {}

    def __save_cache(self) -> None:
        """将新缓存写入文件"""
        with open(".cache.json", "w") as f:
            json.dump(self.data, f, indent=4)

    def __prepare(self, rule: Rule, old_data: dict):
        logger = getLogger("PyMake-Prepare")
        target = rule.product
        target = os.path.normpath(target)
        target_d = os.path.dirname(target)
        if target_d and not os.path.exists(target_d):
            os.makedirs(target_d, exist_ok=True)
        target_data = {}
        deps = {}
        rebuild = False
        if rule.dependencies:
            deps["$" + funhash(rule.build_func)] = rule.dependencies
            logger.debug(f"Found dep from rule: {rule.dependencies}")
        if os.path.exists(target):
            current_hash = calchash(target)
            if current_hash != old_data.get("hash"):
                logger.debug("Hash Changed!")
                rebuild = True
                target_data["hash"] = current_hash

                for trace in rule.tracers:
                    deps["@" + funhash(trace)] = sorted(
                        os.path.normpath(i) for i in trace(target)
                    )
                    logger.debug(f"Found dep from trace: {deps["@"+funhash(trace)]}")
            else:
                logger.debug("Hash not changed!")
                unchecked_tracers = {"@"+funhash(tracer): tracer for tracer in rule.tracers}
                for k, v in old_data.get("dependencies", {}).items():
                    if k in unchecked_tracers:
                        deps[k] = v
                        unchecked_tracers.pop(k)
                for k, t in unchecked_tracers.items():
                    deps[k] = t(rule.product)
        else:
            logger.debug("File not found, rebuild!")
            rebuild = True

        if old_data.get("dependencies") != deps:
            rebuild = True
        target_data["dependencies"] = deps

        all_deps = []
        for i in deps.values():
            all_deps.extend(os.path.normpath(j) for j in i)
        all_deps = sorted({*all_deps})  # 处理一些奇奇怪怪的情况

        logger.debug(f"Final: {target_data}")
        return rebuild, all_deps, target_data

    def __wait_deps(self, deps: list, status: dict):
        logger = getLogger("PyMake-Wait")
        hash_futures = {}
        rebuild = False
        for dep in deps:
            dep = os.path.normpath(dep)
            id = status.get(dep)
            if id:
                logger.debug(f"Waiting for {id}")
                self.dispatcher.end(id)
                rebuild = True
        missing_buildable = []
        for dep in deps:
            if not os.path.exists(dep) and dep in self.config.rules:
                missing_buildable.append(dep)
        for dep in missing_buildable:
            logger.debug(f"Submitting build for missing dependency: {dep}")
            fut = self.dispatcher.begin(self.build, dep)
            status[dep] = fut
        for dep in missing_buildable:
            self.dispatcher.end(status[dep])
            rebuild = True
        for dep in deps:
            dep = os.path.normpath(dep)
            hash_futures[dep] = self.dispatcher.begin(calchash, dep)
        for dep in deps:
            dep = os.path.normpath(dep)
            current_hash = self.dispatcher.end(hash_futures[dep])
            if current_hash != self.data.get(dep,{}).get("hash"):
                rebuild = True
                self.data[dep] = self.data.get(dep, {})
                self.data[dep]["hash"] = current_hash
        return rebuild

    def build(self, target: str, ):
        logger = getLogger("PyMake")
        
        status = {}
        for rule in self.yield_queue(target):
            logger.debug(f"Current Rule: {rule!r}")
            rebuild, all_deps, target_data = self.__prepare(rule, self.data.get(rule.product, {}))
            self.data[rule.product] = target_data
            logger.debug(f"Prepare: rebuild={rebuild!r};all_deps={all_deps!r};target_data={target_data}")
            deps_rebuilt = self.__wait_deps(all_deps, status)
            logger.debug(f"Wait: deps_rebuilt={deps_rebuilt!r}")
            if rebuild or deps_rebuilt:
                status[rule.product] = self.dispatcher.begin(
                    rule.build_func, rule.product, rule.dependencies
                )
                logger.info(f"Task add: {rule.build_func} as {status[rule.product]}")
            logger.debug("")
        ti = status.get(target)
        if ti:
            self.dispatcher.end(ti)
        logger.debug(f"saving: {self.data}")
        self.__save_cache()
        return True

    def call_command(self, name: str):
        id = self.dispatcher.begin(self.config.commands[name])
        return self.dispatcher.end(id)
