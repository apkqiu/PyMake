# PyMake

> 一个为**操作系统开发**而生的 Python 构建系统 —— 零安装、零污染、纯本地、固定版本。

PyMake 不是 Make 的 Python 重写，而是一个**基于 Hash 指纹的增量并行任务调度内核**。它把“构建规则”和“构建调度”彻底分开，让你用纯 Python 定义任何你想定义的构建流程——从编译内核到组装磁盘镜像，从引导交叉编译器到运行 QEMU 虚拟机。

**核心承诺**：`git clone` 下来，编写文件，直接 `python make.py`，就能开始构建。不需要 `pip install`，不需要设置 `PYTHONPATH`，不需要修改系统任何文件。

---

## 设计哲学

- **零系统污染**：绝不往 `/usr/bin`、`~/.local` 或任何系统路径写东西。所有工具链、缓存、日志都留在项目目录内。
- **固定版本**：通过 Git Submodule 锁定构建系统自身的版本。你的项目依赖的是**某个确定的 commit**，而不是“最新版 PyPI 包”。
- **语言无关**：不绑定 C/C++/Rust。构建函数就是 Python 函数，你想调 `gcc`、`nasm`、`qemu`、`protoc` 还是 `python` 自己都行。
- **增量编译**：基于文件内容 **BLAKE2 Hash** 判断是否需要重建，比 `make` 的时间戳更可靠。连构建函数本身的代码变了，也会触发重建。
- **并行调度**：默认 8 线程并发执行无依赖的任务，支持自定义 `Dispatcher`。

---

## 快速开始

### 1. 作为 Submodule 引入（对于git项目）

```bash
git submodule add https://github.com/apkqiu/PyMake.git builder
```

然后在你的项目根目录创建一个 `make.py`：

```python
#!/usr/bin/env python3
from builder import MakeConfig

d = MakeConfig()

@d.rule("hello.txt", ["input.txt"])
def build_hello(dst, src):
    with open(dst, "w") as f:
        f.write(f"Hello from {src[0]}")

d.default = "hello.txt"
```

直接运行：

```bash
chmod +x make.py
./make.py
```

### 2. 直接 Clone 使用

```bash
git clone https://github.com/apkqiu/PyMake.git
cd PyMake
./make.py --list-targets
```

---

## 核心概念

### 规则（Rule）

规则定义“如何从依赖生成目标”：

```python
@d.rule("build/kernel/kernel.elf", ["src/kernel/main.c", "src/kernel/linker.ld"])
def link_kernel(dst, src):
    execute("ld", "-T", src[1], "-o", dst, src[0])
```

- **目标（product）**：要生成的文件路径。
- **依赖（dependencies）**：可以是文件路径字符串，也可以是列表，支持嵌套。
- **构建函数（build_func）**：接收 `(dst, src_list)`，执行任意 Python 逻辑。

### 追踪器（Tracer）

追踪器在**构建前**静态扫描源文件，辅助发现隐式依赖（如 `#include` 的头文件），并注入到依赖图中：

```python
@define_tracer("gcc")
def trace_gcc(file: str):
    out = execute("gcc", "-MM", "-Isrc/include", file, capture=True)
    # 解析输出，返回头文件列表
    return [...]

# 在规则上挂载追踪器
d.trace_rule("gcc", "src/kernel/main.c")
```

这样，修改一个头文件，所有依赖它的 `.c` 文件都会被自动重新编译——不需要手动在 `dependencies` 里列出一长串头文件。

### 命令（Command）

命令是“一次性任务”，不参与依赖图，适合清理、运行模拟器、构建工具链等：

```python
@d.command("clean")
def clean():
    execute("rm", "-rf", "build", ".cache.json", "logs")

@d.command("run")
def run_qemu():
    execute("qemu-system-x86_64", "-drive", "file=os.img", "-m", "2G")
```

执行：`./make.py --command clean`

---

## 目录结构（建议）

```
your-project/
├── builder/               # PyMake Submodule（或直接复制）
│   ├── __init__.py
│   ├── make_config.py
│   ├── make_factory.py
│   └── ...
├── make.py                # 根配置（入口脚本）
├── src/                   # 你的源码
│   ├── boot/
│   ├── kernel/
│   └── ...
├── build/                 # 构建产物（自动生成）
├── logs/                  # 执行日志（自动生成）
└── .cache.json            # Hash 缓存（自动生成）
```

---

## 命令行参数

| 参数 | 说明 |
| :--- | :--- |
| `./make.py` | 构建默认目标（`d.default`） |
| `-t TARGET` | 构建指定目标 |
| `-c COMMAND` | 执行指定命令 |
| `--list-targets` | 列出所有规则及其依赖 |
| `--list-commands` | 列出所有命令 |
| `-v LEVEL` | 设置日志级别（DEBUG/INFO/WARNING/ERROR） |

---

## 案例：编译一个 x86_64 操作系统

PyMake 最初就是为这个场景设计的。完整的操作系统构建流程：

[https://github.com/apkqiu/apkqiu-os](https://github.com/apkqiu/apkqiu-os)

---

## 与 Make 的对比

| 特性 | Make | PyMake |
| :--- | :--- | :--- |
| 规则定义语言 | Makefile 语法 | **Python** |
| 增量判断依据 | 文件修改时间 | **文件内容 Hash** |
| 隐式依赖扫描 | 需手写或借助 `gcc -MM` | **Tracer 机制**，可自定义 |
| 并行控制 | `-j` 参数 | 默认 8 线程，可替换 Dispatcher |
| 跨平台 | 依赖 shell | **纯 Python**，跨平台 |
| 调试体验 | `make -d` 输出难以阅读 | **Python 原生调试**，`print` 随便插 |
| 扩展性 | 有限（函数/宏） | **无限**（任意 Python 代码） |

---

## 为什么没有 `src/` 目录？

PyMake 本身作为一个 **Git Submodule**，被设计为直接挂载在父项目的根目录下（`builder/`）。如果把 PyMake 的源码放在 `builder/src/builder/` 里，父项目的 `import builder` 就会失效。

这是**刻意为之**的设计决策，目的是保证“克隆即用、零配置”。

---

## 许可证

GPLv3 © apkqiu

---

## 最后

如果你真的用这个玩意儿编译出了一个能跑的软件，请务必告诉我——我会很高兴知道，它除了我之外，还真的被第二个人用过了。
