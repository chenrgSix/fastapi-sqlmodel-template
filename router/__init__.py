import inspect
import logging
from datetime import datetime
from functools import wraps
from typing import Union, Type, Callable, TypeVar, get_type_hints

import pytz
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from starlette.responses import JSONResponse

from config import get_settings
from entity.dto import HttpResp, ApiResponse
from exceptions.base import AppException
from utils import get_uuid

__all__ = ["unified_resp", "BaseController"]
RT = TypeVar('RT')  # 返回类型


def unified_resp(func: Callable[..., RT]) -> Callable[..., RT]:
    """统一响应格式
        接口正常返回时,统一响应结果格式
    """
    # 获取原始函数的返回类型注解
    hints = get_type_hints(func)
    return_type = hints.get('return', None)

    # 修改函数的返回类型注解
    if return_type:
        func.__annotations__['return'] = ApiResponse[return_type]

    @wraps(func)
    async def wrapper(*args, **kwargs) -> RT:
        if inspect.iscoroutinefunction(func):
            resp = await func(*args, **kwargs) or []
        else:
            resp = func(*args, **kwargs) or []

        return JSONResponse(
            content=jsonable_encoder(
                # 正常请求响应
                {'code': HttpResp.SUCCESS.code, 'msg': HttpResp.SUCCESS.msg, 'data': resp},
                by_alias=False,
                # 自定义日期时间格式编码器
                custom_encoder={
                    datetime: lambda dt: dt.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(get_settings().timezone))
                    .strftime(get_settings().datetime_fmt)}),
            media_type='application/json;charset=utf-8'
        )

    return wrapper


class BaseController:

    def __init__(self, service):
        self.service = service

    async def base_page(self, req: Union[dict, BaseModel], dto_class: Type[BaseModel] = None):
        if not isinstance(req, dict):
            req = req.model_dump()
        result = await self.service.get_by_page(req,dto_class)
        # datas = result.data
        # if datas and dto_class:
        #     result.data = self.service.entity_conversion_dto(datas, dto_class)
        return result

    async def base_list(self, req: Union[dict, BaseModel], dto_class: Type[BaseModel] = None):
        if not isinstance(req, dict):
            req = req.model_dump()
        datas = await self.service.get_list(req,dto_class)
        return datas


    async def get_by_id(self, id: str, dto_class: Type[BaseModel] = None):
        result = await self.service.get_by_id(id,dto_class)
        if not result:
            raise AppException(f"不存在 id 为{id}的数据")
        return result

    async def add(self, req: Union[dict, BaseModel]):
        if not isinstance(req, dict):
            req = req.model_dump()
        req["id"] = get_uuid()
        try:
            return await self.service.save(**req)
        except Exception as e:
            logging.exception(e)
            raise AppException(f"添加失败, error: {str(e)}")

    async def delete(self, id: str, db_query_data=None):
        if db_query_data is None:
            db_query_data = await self.service.get_by_id(id)
            if not db_query_data:
                raise AppException(f"数据不存在")
        await self.service.check_base_permission(db_query_data)
        try:
            return await self.service.delete_by_id(id)
        except Exception as e:
            logging.exception(e)
            raise AppException(f"删除失败")

    async def update(self, request: BaseModel, db_query_data=None):
        params = request.model_dump()
        req = {k: v for k, v in params.items() if v is not None}
        data_id = req.get("id")
        if db_query_data is None:
            db_query_data = await self.service.get_by_id(data_id)
            if not db_query_data:
                raise AppException(f"数据不存在")
        await self.service.check_base_permission(db_query_data)

        try:
            return await self.service.update_by_id(data_id, req)
        except Exception as e:
            logging.exception(e)
            raise AppException(f"更新失败, error: {str(e)}")
