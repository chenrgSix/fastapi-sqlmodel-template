from sqlalchemy import Column, BigInteger

from common.global_enums import IsDelete
from utils import current_timestamp

# 上下文变量，控制是否启用逻辑删除过滤
_SOFT_DELETE_ENABLED = True
from sqlmodel import SQLModel, Field


class DbBaseModel(SQLModel, table=False):
    id: str = Field(default=None, max_length=32, primary_key=True)
    created_time: int = Field(sa_column=Column(BigInteger), default_factory=current_timestamp)
    # created_by = CharField(max_length=32, index=True)
    updated_time: int = Field(sa_column=Column(BigInteger, onupdate=current_timestamp),
                              default_factory=current_timestamp)
    # updated_by = CharField(max_length=32)
    is_deleted: int = Field(default=IsDelete.NO_DELETE)

    # class Config:
    #     arbitrary_types_allowed = True
