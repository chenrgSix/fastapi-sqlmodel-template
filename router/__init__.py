import logging
from typing import Union, Type

from pydantic import BaseModel

from exceptions.base import AppException
from utils import get_uuid


class BaseController:

    def __init__(self, service):
        self.service = service

    async def base_page(self, req: Union[dict, BaseModel], dto_class: Type[BaseModel] = None):
        if not isinstance(req, dict):
            req = req.model_dump()
        result = await self.service.get_by_page(req)
        datas = result.data
        if datas and dto_class:
            result.data = self.service.entity_conversion_dto(datas, dto_class)
        return result

    async def base_list(self, req: Union[dict, BaseModel], dto_class: Type[BaseModel] = None):
        if not isinstance(req, dict):
            req = req.model_dump()
        datas = await self.service.get_list(req)
        if datas and dto_class:
            datas = self.service.entity_conversion_dto(datas, dto_class)
        return datas

    async def get_all(self, dto_class: Type[BaseModel] = None):
        result = await self.service.get_all()
        if dto_class:
            result = self.service.entity_conversion_dto(result, dto_class)
        return result

    async def get_by_id(self, id: str, dto_class: Type[BaseModel] = None):
        data = await self.service.get_by_id(id)
        if not data:
            raise AppException(f"不存在 id 为{id}的数据")
        result = data.to_dict()
        if dto_class:
            result = self.service.entity_conversion_dto(result, dto_class)
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
        self.service.check_base_permission(db_query_data)
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
        self.service.check_base_permission(db_query_data)

        try:
            return await self.service.update_by_id(data_id, req)
        except Exception as e:
            logging.exception(e)
            raise AppException(f"更新失败, error: {str(e)}")
