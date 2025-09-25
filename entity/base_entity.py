from sqlalchemy import Column, BigInteger, Select, Delete, Update

from common.global_enums import IsDelete
from utils import current_timestamp, get_uuid

# 上下文变量，控制是否启用逻辑删除过滤
_SOFT_DELETE_ENABLED = True
from sqlmodel import SQLModel, Field


class DbBaseModel(SQLModel, table=False):
    id: str = Field(default_factory=get_uuid, max_length=32, primary_key=True)
    created_time: int = Field(
        default_factory=current_timestamp,
        sa_type=BigInteger,
        description="创建时间"
    )
    # created_by = CharField(max_length=32, index=True)
    updated_time: int = Field(
        default_factory=current_timestamp,
        sa_type=BigInteger,
        sa_column_kwargs={"onupdate": current_timestamp},
        description="更新时间"
    )
    # updated_by = CharField(max_length=32)
    is_deleted: int = Field(default=IsDelete.NO_DELETE)

    # class Config:
    #     arbitrary_types_allowed = True
    @classmethod
    def select(cls, fields=None):
        if fields is None:
            fields = cls
        return Select(fields)


    @classmethod
    def delete(cls):
        return Delete(cls)

    @classmethod
    def update(cls):
        return Update(cls)


    @classmethod
    def update_by_ids(cls, ids: list[str],update_dict: dict):
        update_dict.pop("id",None)
        return Update(cls).where(cls.id.in_(ids)).values(**update_dict)
