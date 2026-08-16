import argparse
import os
import sys
from logging import getLevelNamesMapping

from .. import __version__
from ..core.dispatcher import ThreadPoolDispatcher
from ..core.make_config import MakeConfig
from ..core.make_factory import MakeFactory
from ..utils.logger import setLevel

indents = []

def push_title(title):
    indents.append([title, 1])

def push_indent(indent_text):
    indents.append([indent_text, 2])

def print_indent(text):
    for i in indents:
        if i[1]:
            print(i[0],end="")
            if i[1] == 1:
                i[1] = 0
        else:
            print(" "*len(i[0]),end="")
    print(text)

def pop():
    indents.pop()

def tree(name: str, cfg: MakeConfig):
    rule = cfg.rules[name]
    print_indent(f"── {rule.product} (Built by: {rule.build_func.__name__})")
    for i in rule.tracers:
        push_indent("  |")
        print_indent(f"── (Tracer) {i.__name__}")
        pop()
    for i in rule.dependencies:
        push_indent("  |")
        tree(i, cfg)
        pop()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-V", "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "-t",
        "--target",
        action="store",
        help="set build target. Override default item defined in your meta file",
    )
    parser.add_argument("-c", "--command", action="store", help="run command.")
    parser.add_argument(
        "-f", "--meta-file", action="store", help="set meta file. Default is 'make.py'"
    )
    parser.add_argument(
        "--list-targets",
        action="store_true",
        help="list targets.",
    )
    parser.add_argument(
        "--list-commands",
        action="store_true",
        help="list commands.",
    )
    parser.add_argument(
        "--tree",
        action="store_true",
        help="list targets using tree.",
    )
    parser.add_argument(
        "-v",
        "--log-level",
        choices=getLevelNamesMapping().keys(),
        help="set log level.",
    )
    args = parser.parse_args()
    if args.log_level:
        setLevel(getLevelNamesMapping()[args.log_level])
    cfg = MakeConfig()
    if args.meta_file:
        cfg.include(args.meta_file)
    else:
        cfg.subdir(os.getcwd())
    args.target = args.target or cfg.default
    factory = MakeFactory(cfg, ThreadPoolDispatcher())

    if args.list_commands:
        for i in cfg.commands:
            print(i)
        return 0
    if args.command:
        return not factory.call_command(args.command)
    if args.list_targets:
        for i in cfg.rules.values():
            print(i.product)
            push_indent("|")
            if i == cfg.default:
                print_indent("> Default")
            if len(i.dependencies) > 0:
                push_title("> Depend on: ")
                for j in i.dependencies:
                    print_indent(j)
                pop()
            if len(i.tracers) > 0:
                push_title("> Traced by: ")
                for j in i.tracers:
                    print_indent(j.__name__)
                pop()
            print_indent(f"> Built by: {i.build_func.__name__}")
            pop()
            print()
        return 0
    if args.tree:
        tree(args.target, cfg)
        return 0
    return not factory.build(args.target)


if __name__ == "__main__":
    sys.exit(main())
