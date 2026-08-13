import hashlib
import importlib
import importlib.machinery
import importlib.util
import inspect
import os
import sys
from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from functools import partial

from .logger import getLogger
from .tracer import get_tracer

KEY_CONFIG_EXPORT = "~!@#$%CFG_EXP*(@*)"


def import_from(file_path: str):
    """
    从指定的 Python 文件加载 MakeConfig 实例。
    返回该文件中定义的 'd' 对象。
    """
    logger = getLogger("PyMakeConfigLoader")
    # file_path = os.path.abspath(file_path)
    module_name = (
        "dispatcher_config_" + hashlib.md5(file_path.encode()).hexdigest()
    )  # 避免名称冲突
    logger.debug("Loading config file " + file_path + " as " + module_name)

    # 创建模块规格
    loader = importlib.machinery.SourceFileLoader(module_name, file_path)
    spec = importlib.util.spec_from_loader(module_name, loader)
    if spec is None:
        raise ImportError(f"Cannot load config from {file_path}")

    spec.submodule_search_locations = [os.getcwd()]
    # 创建模块对象
    module = importlib.util.module_from_spec(spec)
    # 将模块加入 sys.modules，以便其中的导入语句能正确工作（如相对导入）
    sys.modules[module_name] = module
    try:
        # 执行模块代码
        spec.loader.exec_module(module)
    except Exception:
        # 如果加载失败，从 sys.modules 中移除
        sys.modules.pop(module_name, None)
        raise

    # 从模块中获取对象
    d = getattr(module, KEY_CONFIG_EXPORT, None)
    if d is None:
        raise ValueError(f"No export config data found in {file_path}")
    return d


def parse_requirements(rs):
    new_rs = []
    if isinstance(rs, str):
        new_rs.extend(i.strip() for i in rs.split(","))
    elif isinstance(rs, Iterable):
        for i in rs:
            new_rs.extend(parse_requirements(i))
    return new_rs


@dataclass
class Rule:
    product: str = ""
    dependencies: list[str] = field(default_factory=list)
    tracers: list[Callable[[str], list[str]]] = field(default_factory=list)
    build_func: Callable[[str, list[str]], None] = lambda a, b: None
    defined_in: str | None = None

class MakeConfig:
    def __init__(self):
        self.rules:dict[str,Rule] = defaultdict(Rule)
        self.commands = {}
        self.default = None
        frame = inspect.currentframe().f_back
        name = frame.f_globals.get("__name__", "")

        if name == "__main__":
            from .builder_main import main as start_build

            start_build()
            # 既然是根调用嘛……那注册函数就跳过！
            sys.exit()
        else:
            frame.f_globals[KEY_CONFIG_EXPORT] = self

    # define command
    def add_command(self, name: str, func: Callable):
        self.commands[name] = func
        return func

    def command(self, name: str):
        return partial(self.add_command, name)

    def add_rule(
        self,
        product: str,
        requirements: list[str] | str | None = None,
        compile_func: Callable[[str, list[str]], None] = lambda a,b:None,
    ):
        self.rules[product].product=product            
        self.rules[product].dependencies=parse_requirements(requirements)
        self.rules[product].build_func=compile_func
        return compile_func

    def rule(self, product: str, requirements: list[str] | str | None = None):
        return partial(self.add_rule, product, requirements)

    def trace_rule(self, lang: str, file: str):
        self.rules[file].product = file
        self.rules[file].tracers.append(get_tracer(lang))

    def extend(self, cfg: "MakeConfig"):
        self.rules.update(cfg.rules)
        self.commands.update(cfg.commands)
        if self.default is None:
            self.default = cfg.default

    def include(self, file: str):
        cfg = import_from(file)
        self.extend(cfg)

    def subdir(self, dir: str):
        frame = inspect.currentframe().f_back
        base_dir = os.path.dirname(frame.f_globals.get("__file__", ""))
        for f in ("make.py", "make", "project.py", "project"):
            name = os.path.join(base_dir, dir, f)
            if os.path.exists(name):
                self.include(name)
                break
