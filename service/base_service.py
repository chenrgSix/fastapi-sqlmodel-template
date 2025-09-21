from typing import Union, Type, List, Any, TypeVar, Generic

from fastapi_pagination import Params, Page
from fastapi_pagination.ext.sqlalchemy import paginate
from pydantic import BaseModel
from sqlalchemy import Select, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.global_context import current_session
from entity.dto.base import BasePageQueryReq, BasePageResp, BaseQueryReq
from utils import get_uuid, current_timestamp



class BaseService:
    model=None # 子类必须指定模型

    @classmethod
    def get_db(cls) -> AsyncSession:
        """获取当前请求的会话"""
        session = current_session.get()
        if session is None:
            raise RuntimeError("No database session in context. "
                               "Make sure to use this service within a request context.")
        return session

    @classmethod
    def entity_conversion_dto(cls, entity_data: Union[list, model], dto: Type[BaseModel]) -> Union[
        BaseModel, List[BaseModel]]:
        dto_list = []
        if not isinstance(entity_data, list):
            return dto(**entity_data.to_dict())
        for entity in entity_data:
            temp = entity
            if not isinstance(entity, dict):
                temp = entity.to_dict()
            dto_list.append(dto(**temp))
        return dto_list


    @classmethod
    async def get_by_page(cls, query_params: Union[dict, BasePageQueryReq]):
        if not isinstance(query_params, dict):
            query_params = query_params.model_dump()
        query_params = {k: v for k, v in query_params.items() if v is not None}
        query_entity = cls.get_query_entity(query_params)
        return await cls.auto_page(query_entity, query_params)
    # @classmethod
    # def count_query(cls,query: Select) -> Select:
    #       # type: ignore
    #     return select(func.count("*")).select_from(count_subquery)

    @classmethod
    async def auto_page(cls, query_entity, query_params: Union[dict, BasePageQueryReq] = None,
                  dto_model_class: Type[BaseModel] = None):
        if not query_params:
            query_params = {}
        if not isinstance(query_params, dict):
            query_params = query_params.model_dump()
        page_number = query_params.get("page_number", 1)
        page_size = query_params.get("page_size", 12)
        desc = query_params.get("desc", "desc")
        orderby = query_params.get("orderby", "created_time")
        # data_count = await sessions.count()
        session = cls.get_db()

        # data_count = session.scalar(cls.count_query(query_entity))
        data_count  =None
        if data_count == 0:
            return BasePageResp(**{
                "page_number": page_number,
                "page_size": page_size,
                "count": data_count,
                "desc": desc,
                "orderby": orderby,
                "data": [],
            })
        if desc == "desc":

            query_entity = query_entity.order_by(getattr(cls.model,orderby).desc())
        else:
            query_entity = query_entity.order_by(getattr(cls.model,orderby).asc())
        query_page_result=await paginate(session,
                                         query_entity,
                                         Params(page=page_number,size=page_size))
        # query_entity = query_entity.offset((page_number - 1) * page_size).limit(page_size)
        # query_exec_result = await session.execute(query_entity)
        # result = query_exec_result.scalars().all()
        # return query_page_result
        result = query_page_result.items
        if dto_model_class is not None:
            result = [dto_model_class(**item) for item in result]
        return BasePageResp(**{
            "page_number": page_number,
            "page_size": page_size,
            "page_count": query_page_result.pages,
            "count": query_page_result.total,
            "desc": desc,
            "orderby": orderby,
            "data": result,
        })

    @classmethod
    def get_list(cls, query_params: Union[dict, BaseQueryReq]):
        if not isinstance(query_params, dict):
            query_params = query_params.model_dump()
        query_params = {k: v for k, v in query_params.items() if v is not None}
        desc = query_params.get("desc", "desc")
        orderby = query_params.get("orderby", "created_time")
        sessions = cls.get_query_entity(query_params)
        if desc == "desc":
            sessions = sessions.order_by(cls.model.getter_by(orderby).desc())
        else:
            sessions = sessions.order_by(cls.model.getter_by(orderby).asc())

        return sessions.scalars().all()

    @classmethod
    def get_id_list(cls, query_params: Union[dict, BaseQueryReq]) -> List[Any]:
        if not isinstance(query_params, dict):
            query_params = query_params.model_dump()
        query_params = {k: v for k, v in query_params.items() if v is not None}
        desc = query_params.get("desc", "desc")
        orderby = query_params.get("orderby", "created_time")
        sessions = cls.model.select(cls.model.id)
        sessions = cls.get_query_entity(query_params, sessions)
        if desc == "desc":
            sessions = sessions.order_by(cls.model.getter_by(orderby).desc())
        else:
            sessions = sessions.order_by(cls.model.getter_by(orderby).asc())
        return [item["id"] for item in sessions.scalars().all()]

    @classmethod
    def save(cls, **kwargs):
        """Save a new record to database.

        This method creates a new record in the database with the provided field values,
        forcing an insert operation rather than an update.

        Args:
            **kwargs: Record field values as keyword arguments.

        Returns:
            Model instance: The created record object.
        """
        # todo
        sample_obj = cls.model(**kwargs).save(force_insert=True)
        return sample_obj > 0


    @classmethod
    def insert_many(cls, data_list, batch_size=100):
        """Insert multiple records in batches.

        This method efficiently inserts multiple records into the database using batch processing.
        It automatically sets creation timestamps for all records.

        Args:
            data_list (list): List of dictionaries containing record data to insert.
            batch_size (int, optional): Number of records to insert in each batch. Defaults to 100.
        """

        with DB.atomic():
            for d in data_list:

                if not d.get("id", None):
                    d["id"] = get_uuid()
                d["created_time"] = current_timestamp()
                # d["create_date"] = datetime_format(datetime.now())
            for i in range(0, len(data_list), batch_size):
                cls.model.insert_many(data_list[i: i + batch_size]).execute()

    @classmethod
    def update_by_id(cls, pid, data):
        # Update a single record by ID
        # Args:
        #     pid: Record ID
        #     data: Updated field values
        # Returns:
        #     Number of records updated
        data["updated_time"] = current_timestamp()
        num = cls.model.update(data).where(cls.model.id == pid).execute()
        return num

    @classmethod
    def update_many_by_id(cls, data_list):
        """Update multiple records by their IDs.

        This method updates multiple records in the database, identified by their IDs.
        It automatically updates the updated_time and update_date fields for each record.

        Args:
            data_list (list): List of dictionaries containing record data to update.
                             Each dictionary must include an 'id' field.
        """

        with DB.atomic():
            for data in data_list:
                data["updated_time"] = current_timestamp()
                # data["update_date"] = datetime_format(datetime.now())
                cls.model.update(data).where(cls.model.id == data["id"]).execute()


    @classmethod
    def get_by_id(cls, pid):
        # Get a record by ID
        # Args:
        #     pid: Record ID
        # Returns:
        #     Tuple of (success, record)
        try:
            obj = cls.model.get_or_none(cls.model.id == pid)
            if obj:
                return True, obj
        except Exception:
            pass
        return False, None

    @classmethod
    def get_by_ids(cls, pids, cols=None):
        # Get multiple records by their IDs
        # Args:
        #     pids: List of record IDs
        #     cols: List of columns to select
        # Returns:
        #     Query of matching records
        if cols:
            objs = cls.model.select(*cols)
        else:
            objs = cls.model.select()
        return objs.where(cls.model.id.in_(pids))


    @classmethod
    def delete_by_id(cls, pid):
        ...
    @classmethod
    def delete_by_ids(cls, pids):
        ...

    @classmethod
    def get_query_entity(cls, query_params, sessions=None):
        if sessions is None:
            sessions = cls.model.select()
        for key, value in query_params.items():
            if hasattr(cls.model, key):
                field = getattr(cls.model, key)
                sessions = sessions.where(field == value)
        return sessions

    @classmethod
    def get_data_count(cls, query_params: dict = None):
        if not query_params:
            raise Exception("参数为空")
        sessions = cls.get_query_entity(query_params)
        return sessions.count()

    @classmethod
    def is_exist(cls, query_params: dict = None):
        return cls.get_data_count(query_params) > 0

