# PyMake

PyMake 是一个轻量级、纯 Python 编写的构建工具，用于替代 Makefile。你可以用熟悉的 Python 语法描述构建规则，自动管理依赖、并行执行、增量编译和缓存校验。

## 核心特性

- ✅ **纯 Python 配置** – 无需学习 Make 语法，直接在 `make.py` 或 `project.py` 中编写规则。
- ⚡ **并行构建** – 自动调度任务并发执行（线程池，默认 16 并发）。
- 🔁 **增量编译** – 基于文件 MD5 哈希，只重建变更的目标。
- 📦 **依赖追踪** – 支持自定义依赖分析器（如 C/C++ 头文件自动扫描）。
- 🧩 **命令行扩展** – 可注册自定义命令（`clean`、`test` 等）。
- 🎨 **彩色日志** – 多级日志输出，方便调试。

## 快速开始

### 1. 编写配置文件

在项目根目录创建 `make.py`（或 `project.py`），内容示例：

```python
from builder import MakeConfig

d = MakeConfig()                # 必须命名为 d
d.default = "output.txt"        # 默认构建目标

@d.register("output.txt", ["input.txt"])
def build(target, deps):
    with open(target, "w") as f:
        f.write("Generated from " + ", ".join(deps))

@d.command("clean")
def clean():
    import os
    os.remove("output.txt")
```

### 2. 运行构建

```bash
python make.py                  # 构建默认目标
python make.py -t output.txt    # 指定目标
python make.py -l               # 列出所有目标
python make.py -c clean         # 执行 clean 命令
python make.py -v DEBUG         # 显示调试日志
```

## 命令行选项

| 选项 | 说明 |
| ------ | ------ |
| `-t TARGET` | 构建指定目标 |
| `-c COMMAND` | 运行自定义命令 |
| `-l` | 列出目标（配合 `-c` 列出命令） |
| `-f FILE` | 指定配置文件（默认自动查找 `make.py` 等） |
| `-v LEVEL` | 日志级别：DEBUG, INFO, WARNING, ERROR, CRITICAL |
| `-V` | 显示版本号 |
| `-h` | 显示帮助 |

## 配置详解

### 定义构建任务

使用 `@d.register` 装饰器：

```python
@d.register("target", ["dep1", "dep2"])
def build_target(target, deps):
    # 构建逻辑
```

或直接调用 `d.add()`：

```python
d.add("target", ["dep1", "dep2"], lambda t, d: print("Building", t))
```

### 注册命令

```python
@d.command("deploy")
def deploy():
    print("Deploying...")
```

### 导入其他配置文件

```python
d.include("subproject/make.py")   # 合并任务和命令
d.subdir("libs")                  # 自动加载子目录下的配置文件
```

### 自动追踪依赖（以 C 语言为例）

首先定义跟踪器（可放在单独文件中）：

```python
from builder import define_tracer

@define_tracer("c")
def trace_c(file):
    deps = []
    with open(file) as f:
        for line in f:
            if line.startswith("#include"):
                # 解析头文件路径并加入 deps
                pass
    return deps
```

然后在配置中：

```python
d.trace("c", "main.c")   # 自动将 main.c 依赖的头文件加入构建依赖
```

## 高级特性

- **并行执行**：只要依赖满足，任务自动并行。
- **缓存管理**：哈希存储在 `.cache.json`，自动持久化。
- **循环依赖检测**：构建前会检测并报错。
- **命令执行工具**：内置 `execute()` 和 `execute_capture()`，可实时打印或捕获外部命令输出。

## 许可证

本项目采用 GPLv3 许可（请自行添加许可证文件）。

---

**注意**：PyMake 要求 Python 3.7+，依赖 `colorlog` 包（用于彩色日志）。首次使用请安装依赖：

```bash
pip install colorlog
```

如有问题，欢迎提交 Issue。
