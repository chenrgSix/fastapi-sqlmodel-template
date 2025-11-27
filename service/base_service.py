from typing import Union, Type, List, Any, TypeVar, Generic, Optional

from fastapi_pagination import Params
from fastapi_pagination.ext.sqlalchemy import paginate
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel

from entity import with_db_session
from entity.dto.base import BasePageQueryReq, BasePageResp, BaseQueryReq
from utils import get_uuid

"""
session.execute： 执行任意数据库操作语句，返回结果需要额外处理获取 数据形式：Row对象（类似元组）
-- exec_result.scalars().all(): 从session.execute的执行结果中获取全部的数据
session.scalars: 只适合单模型查询（不适合指定列或连表查询），返回结果需要处理 数据形式：直接返回模型实例（如User对象）
-- 处理exec_result.all(): 从session.scalars的执行结果中获取全部的数据
session.scalar: 直接明确获取一条数据，可以直接返回，无需额外处理

"""
T = TypeVar('T', bound=SQLModel)


class BaseService(Generic[T]):
    model: Type[T]  # 子类必须指定模型

    @classmethod
    def get_query_stmt(cls, query_params, stmt=None, *, fields: list = None):
        if stmt is None:
            if fields:
                stmt = cls.model.select(*fields)
            else:
                stmt = cls.model.select()
        for key, value in query_params.items():
            if value is None:
                continue
            if isinstance(key, str) and hasattr(cls.model, key):  # 第一步：先确定 key 的类型
                # 第二步：根据类型，用对应的方式处理
                field = getattr(cls.model, key)
            elif hasattr(key, 'model') and key.model is cls.model:
                field = key
            else:
                continue
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
                temp = entity.model_dump()
            dto_list.append(dto(**temp))
        return dto_list

    @classmethod
    def check_base_permission(cls, daba: Any):
        # todo
        pass

    @classmethod
    async def get_by_page(cls, query_params: Union[dict, BasePageQueryReq]) -> BasePageResp[T]:
        if not isinstance(query_params, dict):
            query_params = query_params.model_dump()
        query_params = {k: v for k, v in query_params.items() if v not in [None, ""]}
        query_stmt = cls.get_query_stmt(query_params)
        return await cls.auto_page(query_stmt, query_params)

    @classmethod
    @with_db_session()
    async def auto_page(cls, query_stmt, query_params: Union[dict, BasePageQueryReq] = None,
                        dto_model_class: Type[BaseModel] = None, *, session: Optional[AsyncSession]) -> \
            BasePageResp[T]:
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
    @with_db_session()
    async def get_list(cls, query_params: Union[dict, BaseQueryReq], *, session: Optional[AsyncSession] = None) -> List[
        T]:
        if not isinstance(query_params, dict):
            query_params = query_params.model_dump()
        query_params = {k: v for k, v in query_params.items() if v not in [None, ""]}
        sort = query_params.get("sort", "desc")
        orderby = query_params.get("orderby", "created_time")
        query_stmt = cls.get_query_stmt(query_params)
        field = getattr(cls.model, orderby)
        if sort == "desc":
            query_stmt = query_stmt.order_by(field.desc())
        else:
            query_stmt = query_stmt.order_by(field.asc())
        if query_params.get("limit", None) is not None:
            query_stmt = query_stmt.limit(query_params.get("limit"))
        exec_result = await session.execute(query_stmt)
        return list(exec_result.scalars().all())

    @classmethod
    @with_db_session()
    async def get_list_json(cls, query_params: Union[dict, BaseQueryReq], *, session: Optional[AsyncSession] = None) -> \
            List[
                T]:
        resp_list = await cls.get_list(query_params, session=session)

        return [i.model_dump() for i in resp_list]

    @classmethod
    @with_db_session()
    async def get_id_list(cls, query_params: Union[dict, BaseQueryReq], *, session: Optional[AsyncSession] = None) -> \
            List[str]:
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
    @with_db_session()
    async def save(cls, *, session: Optional[AsyncSession] = None, **kwargs) -> T:

        sample_obj = cls.model(**kwargs)
        session.add(sample_obj)
        await session.flush()
        return sample_obj

    @classmethod
    @with_db_session()
    async def save_entity(cls, db_model: SQLModel, *, session: Optional[AsyncSession] = None) -> T:
        session.add(db_model)
        await session.flush()
        return db_model

    @classmethod
    @with_db_session()
    async def insert_many(cls, data_list, batch_size=100, *, session: Optional[AsyncSession] = None) -> None:
        async with session:
            for d in data_list:
                if not d.get("id", None):
                    d["id"] = get_uuid()

            for i in range(0, len(data_list), batch_size):
                session.add_all(data_list[i: i + batch_size])

    @classmethod
    @with_db_session()
    async def update_by_id(cls, pid, data, *, session: Optional[AsyncSession] = None) -> int:
        update_stmt = cls.model.update().where(cls.model.id == pid).values(**data)
        result = await session.execute(update_stmt)
        return result.rowcount

    @classmethod
    @with_db_session()
    async def update_many_by_id(cls, data_list, *, session: Optional[AsyncSession] = None) -> None:
        async with session:
            for data in data_list:
                stmt = cls.model.update().where(cls.model.id == data["id"]).values(**data)
                await session.execute(stmt)

    @classmethod
    @with_db_session()
    async def get_by_id(cls, pid, *, session: Optional[AsyncSession] = None) -> T:

        stmt = cls.model.select().where(cls.model.id == pid)
        return await session.scalar(stmt)

    @classmethod
    @with_db_session()
    async def get_one(cls, query_params: Union[dict, BaseQueryReq], *, session: Optional[AsyncSession] = None) -> T:

        if not isinstance(query_params, dict):
            query_params = query_params.model_dump()
        query_params = {k: v for k, v in query_params.items() if v not in [None, ""]}
        query_stmt = cls.get_query_stmt(query_params)
        return await session.scalar(query_stmt)

    @classmethod
    @with_db_session()
    async def get_by_ids(cls, pids, cols=None, *, session: Optional[AsyncSession] = None) -> List[T]:

        if cols:
            objs = cls.model.select(*cols)
        else:
            objs = cls.model.select()
        stmt = objs.where(cls.model.id.in_(pids))
        result = await session.scalars(stmt)
        return list(result.all())

    @classmethod
    @with_db_session()
    async def delete(cls, delete_params: dict, *, session: Optional[AsyncSession] = None) -> int:

        del_stmt = cls.model.delete()
        for k, v in delete_params.items():
            del_stmt = del_stmt.where(getattr(cls.model, k) == v)
        exec_result = await session.execute(del_stmt)
        return exec_result.rowcount

    @classmethod
    @with_db_session()
    async def delete_by_id(cls, pid, *, session: Optional[AsyncSession] = None) -> int:

        del_stmt = cls.model.delete().where(cls.model.id == pid)
        exec_result = await session.execute(del_stmt)
        return exec_result.rowcount

    @classmethod
    @with_db_session()
    async def delete_by_ids(cls, pids, *, session: Optional[AsyncSession] = None) -> int:

        del_stmt = cls.model.delete().where(cls.model.id.in_(pids))
        result = await session.execute(del_stmt)
        return result.rowcount

    @classmethod
    @with_db_session()
    async def get_data_count(cls, query_params: dict = None, *, session: Optional[AsyncSession] = None) -> int:

        if not query_params:
            raise Exception("参数为空")
        stmt = cls.get_query_stmt(query_params, fields=[func.count(cls.model.id)])
        # stmt = cls.get_query_stmt(query_params)
        return await session.scalar(stmt)

    @classmethod
    async def is_exist(cls, query_params: dict = None):
        return await cls.get_data_count(query_params) > 0
