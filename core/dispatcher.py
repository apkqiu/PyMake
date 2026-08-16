import abc
import concurrent.futures
from collections.abc import Callable
from typing import Any


class Dispatcher(abc.ABC):
    # 开始，不保证立即开始
    @abc.abstractmethod
    def begin(self, func: Callable, *args, **kwargs) -> Any: ...
    # 结束，保证等待结束，返回是否成功；
    @abc.abstractmethod
    def end(self, id: Any) -> Any: ...


class SimpleDispatcher(Dispatcher):
    def begin(self, func: Callable, *args, **kwargs) -> tuple:
        return (func, args, kwargs)
    def end(self, id: tuple):
        return id[0](*id[1], **id[2])


class ThreadPoolDispatcher(Dispatcher):
    def __init__(self, workers=8):
        self.pool = concurrent.futures.ThreadPoolExecutor(workers)

    def begin(self, func: Callable, *args, **kwargs) -> Any:
        return self.pool.submit(func, *args, **kwargs)

    def end(self, id: concurrent.futures.Future):
        return id.result()