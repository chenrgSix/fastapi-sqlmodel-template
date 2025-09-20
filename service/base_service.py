from typing import Union, Type, List, Any, TypeVar, Generic

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.global_context import current_session
from utils import get_uuid, current_timestamp

T = TypeVar('T')


class BaseService(Generic[T]):
    model: Type[T] # 子类必须指定模型

    @classmethod
    def get_db(cls) -> AsyncSession:
        """获取当前请求的会话"""
        session = current_session.get()
        if session is None:
            raise RuntimeError("No database session in context. "
                               "Make sure to use this service within a request context.")
        return session

    @classmethod
    async def create(cls, **kwargs) -> T:
        """通用创建方法"""
        obj = cls.model(**kwargs)
        db = cls.get_db()
        db.add(obj)
        await db.flush()
        return obj

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
    def query(cls, cols=None, reverse=None, order_by=None, **kwargs):
        """Execute a database query with optional column selection and ordering.

        This method provides a flexible way to query the database with various filters
        and sorting options. It supports column selection, sort order control, and
        additional filter conditions.

        Args:
            cols (list, optional): List of column names to select. If None, selects all columns.
            reverse (bool, optional): If True, sorts in descending order. If False, sorts in ascending order.
            order_by (str, optional): Column name to sort results by.
            **kwargs: Additional filter conditions passed as keyword arguments.

        Returns:
            peewee.ModelSelect: A query result containing matching records.
        """
        return cls.model.query(cols=cols, reverse=reverse, order_by=order_by, **kwargs)

    @classmethod
    def get_all(cls, cols=None, reverse=None, order_by=None):
        """Retrieve all records from the database with optional column selection and ordering.

        This method fetches all records from the model's table with support for
        column selection and result ordering. If no order_by is specified and reverse
        is True, it defaults to ordering by created_time.

        Args:
            cols (list, optional): List of column names to select. If None, selects all columns.
            reverse (bool, optional): If True, sorts in descending order. If False, sorts in ascending order.
            order_by (str, optional): Column name to sort results by. Defaults to 'created_time' if reverse is specified.

        Returns:
            peewee.ModelSelect: A query containing all matching records.
        """
        if cols:
            query_records = cls.model.select(*cols)
        else:
            query_records = cls.model.select()
        if reverse is not None:
            if not order_by or not hasattr(cls, order_by):
                order_by = "created_time"
            if reverse is True:
                query_records = query_records.order_by(cls.model.getter_by(order_by).desc())
            elif reverse is False:
                query_records = query_records.order_by(cls.model.getter_by(order_by).asc())
        return query_records

    @classmethod
    def get(cls, **kwargs):
        """Get a single record matching the given criteria.

        This method retrieves a single record from the database that matches
        the specified filter conditions.

        Args:
            **kwargs: Filter conditions as keyword arguments.

        Returns:
            Model instance: Single matching record.

        Raises:
            peewee.DoesNotExist: If no matching record is found.
        """
        return cls.model.get(**kwargs)

    @classmethod
    def get_or_none(cls, **kwargs):
        """Get a single record or None if not found.

        This method attempts to retrieve a single record matching the given criteria,
        returning None if no match is found instead of raising an exception.

        Args:
            **kwargs: Filter conditions as keyword arguments.

        Returns:
            Model instance or None: Matching record if found, None otherwise.
        """
        try:
            return cls.model.get(**kwargs)
        except peewee.DoesNotExist:
            return None

    @classmethod
    def get_by_page(cls, query_params: Union[dict, BasePageQueryReq]):
        if not isinstance(query_params, dict):
            query_params = query_params.model_dump()
        query_params = {k: v for k, v in query_params.items() if v is not None}
        sessions = cls.get_query_session(query_params)
        return cls.auto_page(sessions, query_params)

    @classmethod
    def auto_page(cls, sessions, query_params: Union[dict, BasePageQueryReq] = None,
                  dto_model_class: Type[BaseModel] = None):
        if not query_params:
            query_params = {}
        if not isinstance(query_params, dict):
            query_params = query_params.model_dump()
        page_number = query_params.get("page_number", 1)
        page_size = query_params.get("page_size", 12)
        desc = query_params.get("desc", "desc")
        orderby = query_params.get("orderby", "created_time")
        data_count = sessions.count()
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
            sessions = sessions.order_by(cls.model.getter_by(orderby).desc())
        else:
            sessions = sessions.order_by(cls.model.getter_by(orderby).asc())
        sessions = sessions.paginate(int(page_number), int(page_size))
        datas = list(sessions.dicts())
        result = datas
        if dto_model_class is not None:
            result = [dto_model_class(**item) for item in datas]
        return BasePageResp(**{
            "page_number": page_number,
            "page_size": page_size,
            "count": data_count,
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
        sessions = cls.get_query_session(query_params)
        if desc == "desc":
            sessions = sessions.order_by(cls.model.getter_by(orderby).desc())
        else:
            sessions = sessions.order_by(cls.model.getter_by(orderby).asc())

        return list(sessions.dicts())

    @classmethod
    def get_id_list(cls, query_params: Union[dict, BaseQueryReq]) -> List[Any]:
        if not isinstance(query_params, dict):
            query_params = query_params.model_dump()
        query_params = {k: v for k, v in query_params.items() if v is not None}
        desc = query_params.get("desc", "desc")
        orderby = query_params.get("orderby", "created_time")
        sessions = cls.model.select(cls.model.id)
        sessions = cls.get_query_session(query_params, sessions)
        if desc == "desc":
            sessions = sessions.order_by(cls.model.getter_by(orderby).desc())
        else:
            sessions = sessions.order_by(cls.model.getter_by(orderby).asc())
        return [item["id"] for item in list(sessions.dicts())]

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

        sample_obj = cls.model(**kwargs).save(force_insert=True)
        return sample_obj > 0

    @classmethod
    def insert(cls, **kwargs):
        """Insert a new record with automatic ID and timestamps.

        This method creates a new record with automatically generated ID and timestamp fields.
        It handles the creation of created_time, create_date, updated_time, and update_date fields.

        Args:
            **kwargs: Record field values as keyword arguments.

        Returns:
            Model instance: The newly created record object.
        """
        if "id" not in kwargs:
            kwargs["id"] = get_uuid()

        kwargs["created_time"] = current_timestamp()
        # kwargs["create_date"] = datetime_format(datetime.now())
        kwargs["updated_time"] = current_timestamp()
        # kwargs["update_date"] = datetime_format(datetime.now())
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
    def updated_by_id(cls, pid, data):
        # Update a single record by ID
        # Args:
        #     pid: Record ID
        #     data: Updated field values
        # Returns:
        #     Number of records updated
        data["updated_time"] = current_timestamp()
        # data["update_date"] = datetime_format(datetime.now())
        num = cls.model.update(data).where(cls.model.id == pid).execute()
        return num > 0

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
    def get_last_by_create_time(cls):
        # Get multiple records by their IDs
        # Args:
        #     pids: List of record IDs
        #     cols: List of columns to select
        # Returns:
        #     Query of matching records
        latest = cls.model.select().order_by(cls.model.created_time.desc()).first()
        return latest

    @classmethod
    def delete_by_id(cls, pid):
        # Delete a record by ID
        # Args:
        #     pid: Record ID
        # Returns:
        #     Number of records deleted
        return cls.model.delete().where(cls.model.id == pid).execute()

    @classmethod
    def delete_by_ids(cls, pids):
        # Delete multiple records by their IDs
        # Args:
        #     pids: List of record IDs
        # Returns:
        #     Number of records deleted
        with DB.atomic():
            res = cls.model.delete().where(cls.model.id.in_(pids)).execute()
            return res

    @classmethod
    def filter_delete(cls, filters):
        # Delete records matching given filters
        # Args:
        #     filters: List of filter conditions
        # Returns:
        #     Number of records deleted
        with DB.atomic():
            num = cls.model.delete().where(*filters).execute()
            return num

    @classmethod
    def filter_update(cls, filters, update_data):
        # Update records matching given filters
        # Args:
        #     filters: List of filter conditions
        #     update_data: Updated field values
        # Returns:
        #     Number of records updated
        with DB.atomic():
            return cls.model.update(update_data).where(*filters).execute()

    @staticmethod
    def cut_list(tar_list, n):
        # Split a list into chunks of size n
        # Args:
        #     tar_list: List to split
        #     n: Chunk size
        # Returns:
        #     List of tuples containing chunks
        length = len(tar_list)
        arr = range(length)
        result = [tuple(tar_list[x: (x + n)]) for x in arr[::n]]
        return result

    @classmethod
    def filter_scope_list(cls, in_key, in_filters_list, filters=None, cols=None):
        # Get records matching IN clause filters with optional column selection
        # Args:
        #     in_key: Field name for IN clause
        #     in_filters_list: List of values for IN clause
        #     filters: Additional filter conditions
        #     cols: List of columns to select
        # Returns:
        #     List of matching records
        in_filters_tuple_list = cls.cut_list(in_filters_list, 20)
        if not filters:
            filters = []
        res_list = []
        if cols:
            for i in in_filters_tuple_list:
                query_records = cls.model.select(*cols).where(getattr(cls.model, in_key).in_(i), *filters)
                if query_records:
                    res_list.extend([query_record for query_record in query_records])
        else:
            for i in in_filters_tuple_list:
                query_records = cls.model.select().where(getattr(cls.model, in_key).in_(i), *filters)
                if query_records:
                    res_list.extend([query_record for query_record in query_records])
        return res_list

    @classmethod
    def get_query_session(cls, query_params, sessions=None):

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
        sessions = cls.get_query_session(query_params)
        return sessions.count()

    @classmethod
    def is_exist(cls, query_params: dict = None):
        return cls.get_data_count(query_params) > 0

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
    def check_base_permission(cls, model_data):
        if isinstance(model_data, dict):
            if model_data.get("created_by") != get_current_user().id:
                raise RuntimeError("无操作权限，该操作仅创建者有此权限")
        if model_data.created_by != get_current_user().id:
            raise RuntimeError("无操作权限，该操作仅创建者有此权限")
