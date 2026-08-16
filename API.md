# API 参考文档

## 模块 `builder`

### `MakeConfig`

```python
class MakeConfig:
    def __init__(self, root_check=True)
```

配置对象，通常以 `d` 命名导出。

**属性**：

- `default: str` – 默认目标。

**方法**：

- `add(product: str, requirements: Union[list[str], str, None], compile_func: Callable[[str, list[str]], None]) -> Callable`
- `register(product: str, requirements: Union[list[str], str, None] = None) -> Callable`
- `command(name: str) -> Callable`
- `trace(lang: str, file: str) -> None`
- `include(file: str) -> None`
- `include_cfg(cfg: MakeConfig) -> None`
- `subdir(dir: str) -> None`

---

### `define_tracer`

```python
def define_tracer(type: str) -> Callable
```

装饰器，用于注册依赖跟踪器。被装饰的函数接收文件路径，返回依赖文件列表。

**示例**：

```python
@define_tracer("cpp")
def trace_cpp(file):
    # parse includes...
    return deps
```

---

### `execute`

```python
def execute(*cmdline, check=True) -> None
```

执行外部命令，实时打印输出。参数可混合字符串和可迭代对象（自动展平）。若 `check=True` 且进程返回非零，抛出 `ChildProcessError`。

---

### `execute_capture`

```python
def execute_capture(*cmdline, check=True) -> str
```

执行命令，捕获输出并返回字符串，同时打印到日志。若 `check=True` 且失败则抛出异常。

---

### `glob`

```python
def glob(pattern: str) -> Iterator[str]
```

递归展开通配符（使用 `glob.iglob`）。

---

### `n`

```python
def n(name: str) -> str
```

返回文件名（去除目录路径和扩展名）。例如 `n("src/foo.c")` → `"foo"`。

---

### `need_build`

```python
def need_build(target: str, dependencies: list[str]) -> bool
```

基于缓存哈希判断目标是否需要重建。如果任何依赖的哈希改变或目标不存在，返回 `True`，否则返回 `False`。

---

### `place_data`

```python
def place_data(key: str, value: Optional[dict] = None) -> dict
```

存储或查询缓存数据。若提供 `value`，则更新 `key` 对应的字典；返回当前 `key` 的旧数据（可能为空字典）。通常内部使用。

---

## 日志模块 `builder.logger`

- `verbose(level: int)`：设置全局日志级别（使用 `logging` 的级别常量）。
- `getLogger(name: str)`：返回配置了彩色控制台输出的 `logging.Logger` 实例。

---

## 系统模块 `builder.system`

包含 `execute` 和 `execute_capture`（见上）。

---

## 跟踪器模块 `builder.tracer`

- `trace_types`：全局字典，存储注册的跟踪器函数。
- `trace(type: str, file: str) -> list[str]`：调用对应跟踪器，返回依赖列表。

---

## 工具模块 `builder.util`

- `make_queue(config, target)`：生成器，构建任务队列（拓扑排序后的任务列表），每个元素为 `(product, req, partial(func, product, req))`。内部使用。
- `calchash(file)`：计算文件的 MD5 哈希。
- `dump_hashes()`：程序退出时自动保存缓存（通过 `atexit` 注册）。
