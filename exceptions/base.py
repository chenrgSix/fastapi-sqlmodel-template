"""全局异常处理
"""
import logging

__all__ = ['AppException']

from enum import IntEnum, Enum


logger = logging.getLogger(__name__)
class CustomEnum(Enum):
    @classmethod
    def valid(cls, value):
        try:
            cls(value)
            return True
        except BaseException:
            return False

    @classmethod
    def values(cls):
        return [member.value for member in cls.__members__.values()]

    @classmethod
    def names(cls):
        return [member.name for member in cls.__members__.values()]


class RetCode(IntEnum, CustomEnum):
    """
     SUCCESS = 0  # 成功
     NOT_EFFECTIVE = 10  # 未生效
     EXCEPTION_ERROR = 100  # 异常错误
     ARGUMENT_ERROR = 101  # 参数错误
     DATA_ERROR = 102  # 数据错误
     OPERATING_ERROR = 103  # 操作错误
     CONNECTION_ERROR = 105  # 连接错误
     RUNNING = 106  # 运行中
     PERMISSION_ERROR = 108  # 权限错误
     AUTHENTICATION_ERROR = 109  # 认证错误
     UNAUTHORIZED = 401  # 未授权
     SERVER_ERROR = 500  # 服务器错误
     FORBIDDEN = 403  # 禁止访问
     NOT_FOUND = 404  # 未找到
     """
    SUCCESS = 0  # 成功
    NOT_EFFECTIVE = 10  # 未生效
    EXCEPTION_ERROR = 100  # 异常错误
    ARGUMENT_ERROR = 101  # 参数错误
    DATA_ERROR = 102  # 数据错误
    OPERATING_ERROR = 103  # 操作错误
    CONNECTION_ERROR = 105  # 连接错误
    RUNNING = 106  # 运行中
    PERMISSION_ERROR = 108  # 权限错误
    AUTHENTICATION_ERROR = 109  # 认证错误
    UNAUTHORIZED = 401  # 未授权
    SERVER_ERROR = 500  # 服务器错误
    FORBIDDEN = 403  # 禁止访问
    NOT_FOUND = 404  # 未找到

class AppException(Exception):
    """应用异常基类
    """

    def __init__(self, msg, *args, code: int = None, echo_exc: bool = False, **kwargs):
        super().__init__()
        self._code = RetCode.SERVER_ERROR.value if code is None else code
        self._message = msg
        self.echo_exc = echo_exc
        self.args = args or []
        self.kwargs = kwargs or {}

    @property
    def code(self) -> int:
        return self._code

    @property
    def msg(self) -> str:
        return self._message

    def __str__(self):
        return '{}: {}'.format(self.code, self.msg)
