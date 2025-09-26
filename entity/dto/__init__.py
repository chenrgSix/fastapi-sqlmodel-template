from collections import namedtuple
from typing import TypeVar, Generic, Optional

from beartype.claw import beartype_this_package
from pydantic import BaseModel

beartype_this_package()
HttpCode = namedtuple('HttpResp', ['code', 'msg'])

T = TypeVar("T")


class HttpResp:
    """HTTP响应结果
    """
    SUCCESS = HttpCode(200, '成功')
    FAILED = HttpCode(300, '失败')
    PARAMS_VALID_ERROR = HttpCode(310, '参数校验错误')
    PARAMS_TYPE_ERROR = HttpCode(311, '参数类型错误')
    REQUEST_METHOD_ERROR = HttpCode(312, '请求方法错误')
    ASSERT_ARGUMENT_ERROR = HttpCode(313, '断言参数错误')

    LOGIN_ACCOUNT_ERROR = HttpCode(330, '登录账号或密码错误')
    LOGIN_DISABLE_ERROR = HttpCode(331, '登录账号已被禁用了')
    TOKEN_EMPTY = HttpCode(332, 'token参数为空')
    TOKEN_INVALID = HttpCode(333, 'token参数无效')

    NO_PERMISSION = HttpCode(403, '无相关权限')
    REQUEST_404_ERROR = HttpCode(404, '请求接口不存在')
    DATA_ALREADY_EXISTS = HttpCode(409, '数据已存在')
    SYSTEM_ERROR = HttpCode(500, '系统错误')
    SYSTEM_TIMEOUT_ERROR = HttpCode(504, '请求超时')


class ApiResponse(BaseModel, Generic[T]):
    code: int = HttpResp.SUCCESS.code
    message: str = HttpResp.SUCCESS.msg
    data: Optional[T] = None
