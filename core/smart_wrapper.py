import asyncio
import inspect
from functools import wraps, partial
from typing import Any, Callable
"""
这个装饰器是用于同步代码，使其支持异步调用，避免阻塞事件事件循环
使用示例代码:

@smart_wrap
def task(seconds):
    time.sleep(seconds)
    return "任务完成"
    
async def task():
    await task(100)
    return "over"
使用装饰器smart_wrap后，该函数可以在异步(协程)函数中执行且不阻塞
"""

class SmartWrapper:
    """
    智能包装器
    自动识别环境判断同步代码是否需要进行异步包装
    """

    def __init__(self, func: Callable):
        self.func = func
        self._is_coroutine = asyncio.iscoroutinefunction(func)
        wraps(func)(self)  # 使用 wraps 保留原始函数的元信息

    def __get__(self, instance, owner):
        """
        描述符协议实现，用于支持实例方法装饰
        """
        if instance is None:
            # 如果通过类访问 (e.g., MyClass.my_method)，返回 self
            return self

        # 如果通过实例访问 (e.g., obj.my_method)，返回一个绑定了实例的新方法
        # partial 会将 instance 作为第一个参数，预填充到 __call__ 中
        return partial(self.__call__, instance)

    def __call__(self, *args, **kwargs):
        """智能调用：自动检测并适配调用环境"""

        # 检测调用环境
        try:
            # 获取当前运行的事件循环
            loop = asyncio.get_running_loop()
            in_async_context = True
        except RuntimeError:
            in_async_context = False

        # 检测调用方式（是否被await）
        caller_frame = inspect.currentframe().f_back
        caller_code = caller_frame.f_code
        is_awaited = 'await' in caller_code.co_names or 'async' in caller_code.co_names

        if in_async_context and is_awaited:
            # 异步环境 + await调用 → 异步执行
            return self._async_call(*args, **kwargs)
        elif not in_async_context:
            # 同步环境 → 同步执行
            return self.func(*args, **kwargs)
        else:
            # 异步环境但没有await → 返回协程
            return self._async_call(*args, **kwargs)

    async def _async_call(self, *args, **kwargs):
        """异步执行"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,  # 使用默认线程池
            lambda: self.func(*args, **kwargs)
        )

    def sync(self, *args, **kwargs):
        """强制同步执行"""
        return self.func(*args, **kwargs)

    async def async_mode(self, *args, **kwargs):
        """强制异步执行"""
        return await self._async_call(*args, **kwargs)


# 便捷装饰器
def smart_wrap(func: Callable):
    return SmartWrapper(func)
