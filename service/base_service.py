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
                stmt = cls.model.select(fields)
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
        """
        数据脱敏
        """
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
    async def check_base_permission(cls, daba: Any):
        # todo
        pass

    @classmethod
    async def get_by_page(cls, query_params: Union[dict, BasePageQueryReq], dto_model_class: Type[BaseModel] = None) -> \
            BasePageResp[T]:
        if not isinstance(query_params, dict):
            query_params = query_params.model_dump()
        query_params = {k: v for k, v in query_params.items() if v not in [None, ""]}
        fields = None
        if dto_model_class is not None:
            fields = [getattr(cls.model, key) for key in dto_model_class.model_fields.keys()]
        query_stmt = cls.get_query_stmt(query_params, fields=fields)

        return await cls.auto_page(query_stmt, query_params, dto_model_class)

    @classmethod
    @with_db_session()
    async def auto_page(cls, query_stmt, query_params: Union[dict, BasePageQueryReq] = None,
                        dto_model_class: Type[BaseModel] = None, *, session: Optional[AsyncSession]) -> BasePageResp[T]:
        if not query_params:
            query_params = {}
        if not isinstance(query_params, dict):
            query_params = query_params.model_dump()
        page_number = query_params.get("page_number", 1)
        page_size = query_params.get("page_size", 12)
        sort = query_params.get("sort", "desc")
        orderby = query_params.get("orderby", "created_time")

        if sort == "desc":
            query_stmt = query_stmt.order_by(getattr(cls.model, orderby).desc())
        else:
            query_stmt = query_stmt.order_by(getattr(cls.model, orderby).asc())

        query_page_result = await paginate(session, query_stmt, Params(page=page_number, size=page_size))
        result = query_page_result.items
        if dto_model_class is not None:
            # 使用 row._mapping 将 Row 对象转换为可解包的字典
            result = [dto_model_class(**dict(row._mapping)) for row in result]
        return BasePageResp(
            **{"page_number": page_number, "page_size": page_size, "page_count": query_page_result.pages,
                "count": query_page_result.total, "sort": sort, "orderby": orderby, "data": result, })

    @classmethod
    @with_db_session()
    async def get_list(cls, query_params: Union[dict, BaseQueryReq], dto_model_class: Type[BaseModel] = None, *,
                       session: Optional[AsyncSession] = None) -> List[T] | List[BaseModel]:
        """
        query_params: 参数字典 or 参数请求模型
        dto_model_class: 输出类型
        session: 数据库会话---支持传递以便于事务管控
        获取数据集合
        """
        query_stmt = cls.build_query(query_params, dto_model_class=dto_model_class)
        exec_result = await session.execute(query_stmt)
        return cls.parse_result(exec_result, dto_model_class=dto_model_class)

    @classmethod
    @with_db_session()
    async def get_id_list(cls, query_params: Union[dict, BaseQueryReq], *, session: Optional[AsyncSession] = None):
        query_stmt = cls.build_query(query_params, fields=[cls.model.id])
        exec_result = await session.scalars(query_stmt)
        return list(exec_result)

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
    async def get_by_ids(cls, pids, dto_model_class: Type[BaseModel] = None, *,
                         session: Optional[AsyncSession] = None) -> List[T]:
        stmt = cls.build_query({}, dto_model_class=dto_model_class)
        stmt = stmt.where(cls.model.id.in_(pids))
        exec_result = await session.execute(stmt)
        return cls.parse_result(exec_result, dto_model_class=dto_model_class)

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

    @classmethod
    def build_query(cls, query_params: Union[dict, BaseQueryReq], *, dto_model_class: Type[BaseModel] = None,
                    fields: List = None):
        """
        可选dto_model_class、fields
        优先级dto_model_class>fields
        如果传递了dto_model_class则无需传递fields，fields会被dto_model_class覆盖
        """
        if not isinstance(query_params, dict):
            query_params = query_params.model_dump()
        query_params = {k: v for k, v in query_params.items() if v not in [None, ""]}
        sort = query_params.get("sort", "desc").lower()
        orderby = query_params.get("orderby", "created_time").lower()
        if dto_model_class is not None:
            # 安全映射：只获取 DTO 中存在且 Model 中也有的字段
            # 避免 DTO 包含计算字段时 getattr 报错
            db_columns = []
            for key in dto_model_class.model_fields.keys():
                if hasattr(cls.model, key):
                    db_columns.append(getattr(cls.model, key))
            fields = db_columns

        query_stmt = cls.get_query_stmt(query_params, fields=fields)

        if hasattr(cls.model, orderby):
            order_field = getattr(cls.model, orderby)
        else:
            # 如果传入的 orderby 字段不存在，回退到默认排序，防止报错
            order_field = cls.model.created_time

        # 根据xxx字段排序
        if sort == "desc":
            query_stmt = query_stmt.order_by(order_field.desc())
        else:
            query_stmt = query_stmt.order_by(order_field.asc())

        if query_params.get("limit", None) is not None:
            query_stmt = query_stmt.limit(query_params.get("limit"))
        return query_stmt

    @classmethod
    def parse_result(cls, exec_result, dto_model_class: Type[BaseModel] = None):
        """
            将数据库执行结果解析为 DTO 列表或 实体列表
        """
        if dto_model_class is not None:
            return [dto_model_class(**dict(row._mapping)) for row in exec_result.all()]
        return list(exec_result.scalars().all())
