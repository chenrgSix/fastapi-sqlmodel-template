from typing import Union, Type, List, Any, TypeVar, Generic, Callable, Coroutine, Optional

from fastapi_pagination import Params
from fastapi_pagination.ext.sqlalchemy import paginate
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from core.global_context import current_session
from entity import DbBaseModel
from entity.dto.base import BasePageQueryReq, BasePageResp, BaseQueryReq
from utils import get_uuid

"""
session.execute： 执行任意数据库操作语句，返回结果需要额外处理获取 数据形式：Row对象（类似元组）
-- exec_result.scalars().all(): 从session.execute的执行结果中获取全部的数据
session.scalars: 只适合单模型查询（不适合指定列或连表查询），返回结果需要处理 数据形式：直接返回模型实例（如User对象）
-- 处理exec_result.all(): 从session.scalars的执行结果中获取全部的数据
session.scalar: 直接明确获取一条数据，可以直接返回，无需额外处理

"""
T = TypeVar('T', bound=DbBaseModel)

class BaseService(Generic[T]):
    model: Type[T]  # 子类必须指定模型

    @classmethod
    def get_db(cls) -> AsyncSession:
        """获取当前请求的会话"""
        session = current_session.get()
        if session is None:
            raise RuntimeError("No database session in context. "
                               "Make sure to use this service within a request context.")
        return session

    @classmethod
    def get_query_stmt(cls, query_params, stmt=None, *, fields: list = None):
        if stmt is None:
            if fields:
                stmt = cls.model.select(*fields)
            else:
                stmt = cls.model.select()
        for key, value in query_params.items():
            if hasattr(cls.model, key) and value is not None:
                field = getattr(cls.model, key)
                stmt = stmt.where(field == value)
        return stmt

    @classmethod
    def entity_conversion_dto(cls, entity_data: Union[list, BaseModel], dto: Type[BaseModel]) -> Union[
        BaseModel, List[BaseModel]]:
        dto_list = []
        if not isinstance(entity_data, list):
            return dto(**entity_data.model_dump())
        for entity in entity_data:
            temp = entity
            if not isinstance(entity, dict):
                temp = entity.to_dict()
            dto_list.append(dto(**temp))
        return dto_list

    @classmethod
    def check_base_permission(cls, daba: Any):
        # todo
        pass

    @classmethod
    async def get_by_page(cls, query_params: Union[dict, BasePageQueryReq])->BasePageResp[T]:
        if not isinstance(query_params, dict):
            query_params = query_params.model_dump()
        query_params = {k: v for k, v in query_params.items() if v not in [None,""]}
        query_stmt = cls.get_query_stmt(query_params)
        return await cls.auto_page(query_stmt, query_params)

    @classmethod
    async def auto_page(cls, query_stmt, query_params: Union[dict, BasePageQueryReq] = None,
                        dto_model_class: Type[BaseModel] = None,*, session: Optional[AsyncSession] = None)->BasePageResp[T]:
        session = session or cls.get_db()
        if not query_params:
            query_params = {}
        if not isinstance(query_params, dict):
            query_params = query_params.model_dump()
        page_number = query_params.get("page_number", 1)
        page_size = query_params.get("page_size", 12)
        sort = query_params.get("sort", "desc")
        orderby = query_params.get("orderby", "created_time")
        data_count = None
        if data_count == 0:
            return BasePageResp(**{
                "page_number": page_number,
                "page_size": page_size,
                "count": data_count,
                "sort": sort,
                "orderby": orderby,
                "data": [],
            })
        if sort == "desc":
            query_stmt = query_stmt.order_by(getattr(cls.model, orderby).desc())
        else:
            query_stmt = query_stmt.order_by(getattr(cls.model, orderby).asc())
        query_page_result = await paginate(session,
                                           query_stmt,
                                           Params(page=page_number, size=page_size))
        result = query_page_result.items
        if dto_model_class is not None:
            result = [dto_model_class(**item) for item in result]
        return BasePageResp(**{
            "page_number": page_number,
            "page_size": page_size,
            "page_count": query_page_result.pages,
            "count": query_page_result.total,
            "sort": sort,
            "orderby": orderby,
            "data": result,
        })

    @classmethod
    async def get_list(cls, query_params: Union[dict, BaseQueryReq],*, session: Optional[AsyncSession] = None)->List[T]:
        session = session or cls.get_db()
        if not isinstance(query_params, dict):
            query_params = query_params.model_dump()
        query_params = {k: v for k, v in query_params.items() if v not in [None,""]}
        sort = query_params.get("sort", "desc")
        orderby = query_params.get("orderby", "created_time")
        query_stmt = cls.get_query_stmt(query_params)
        field = getattr(cls.model, orderby)
        if sort == "desc":
            query_stmt = query_stmt.order_by(field.desc())
        else:
            query_stmt = query_stmt.order_by(field.asc())
        exec_result = await session.execute(query_stmt)
        return list(exec_result.scalars().all())

    @classmethod
    async def get_id_list(cls, query_params: Union[dict, BaseQueryReq],*, session: Optional[AsyncSession] = None) -> List[str]:
        session = session or cls.get_db()
        if not isinstance(query_params, dict):
            query_params = query_params.model_dump()
        query_params = {k: v for k, v in query_params.items() if v is not None}
        sort = query_params.get("sort", "desc")
        orderby = query_params.get("orderby", "created_time")
        query_stmt = cls.model.select(cls.model.id)
        query_stmt = cls.get_query_stmt(query_params, query_stmt)
        if sort == "desc":
            query_stmt = query_stmt.order_by(cls.model.getter_by(orderby).desc())
        else:
            query_stmt = query_stmt.order_by(cls.model.getter_by(orderby).asc())
        exec_result = await session.execute(query_stmt)
        return [item["id"] for item in exec_result.scalars().all()]

    @classmethod
    async def save(cls,*, session: Optional[AsyncSession] = None, **kwargs)->T:
        session = session or cls.get_db()
        sample_obj = cls.model(**kwargs)
        session.add(sample_obj)
        await session.flush()
        return sample_obj

    @classmethod
    async def insert_many(cls, data_list, batch_size=100,*, session: Optional[AsyncSession] = None)->None:
        session = session or cls.get_db()
        async with session:
            for d in data_list:
                if not d.get("id", None):
                    d["id"] = get_uuid()

            for i in range(0, len(data_list), batch_size):
                session.add_all(data_list[i: i + batch_size])

    @classmethod
    async def update_by_id(cls, pid, data,*, session: Optional[AsyncSession] = None)-> int:
        session = session or cls.get_db()
        update_stmt = cls.model.update().where(cls.model.id == pid).values(**data)
        result = await session.execute(update_stmt)
        return result.rowcount

    @classmethod
    async def update_many_by_id(cls, data_list,*, session: Optional[AsyncSession] = None)->None:
        session = session or cls.get_db()
        async with session:
            for data in data_list:
                stmt = cls.model.update().where(cls.model.id == data["id"]).values(**data)
                await session.execute(stmt)

    @classmethod
    async def get_by_id(cls, pid,*, session: Optional[AsyncSession] = None)->T:
        session = session or cls.get_db()
        stmt = cls.model.select().where(cls.model.id == pid)
        return await session.scalar(stmt)


    @classmethod
    async def get_by_ids(cls, pids, cols=None,*, session: Optional[AsyncSession] = None)->List[T]:
        session = session or cls.get_db()
        if cols:
            objs = cls.model.select(*cols)
        else:
            objs = cls.model.select()
        stmt = objs.where(cls.model.id.in_(pids))
        result = await session.scalars(stmt)
        return list(result.all())

    @classmethod
    async def delete_by_id(cls, pid,*, session: Optional[AsyncSession] = None)-> int:
        session = session or cls.get_db()
        del_stmt = cls.model.delete().where(cls.model.id == pid)
        exec_result = await session.execute(del_stmt)
        return exec_result.rowcount

    @classmethod
    async def delete_by_ids(cls, pids,*, session: Optional[AsyncSession] = None)-> int:
        session = session or cls.get_db()
        del_stmt = cls.model.delete().where(cls.model.id.in_(pids))
        result = await session.execute(del_stmt)
        return result.rowcount

    @classmethod
    async def get_data_count(cls, query_params: dict = None,*, session: Optional[AsyncSession] = None) -> int:
        session = session or cls.get_db()
        if not query_params:
            raise Exception("参数为空")
        stmt = cls.get_query_stmt(query_params, fields=[func.count(cls.model.id)])
        # stmt = cls.get_query_stmt(query_params)
        return await session.scalar(stmt)

    @classmethod
    async def is_exist(cls, query_params: dict = None):
        return await cls.get_data_count(query_params) > 0
