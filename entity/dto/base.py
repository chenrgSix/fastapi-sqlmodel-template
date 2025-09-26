from typing import Optional, List, Any, Generic, TypeVar
from typing import Union

from pydantic import BaseModel, Field

T = TypeVar('T')

class BaseTabelDto(BaseModel):
    id: Optional[str] = None
    created_time: Optional[int] = None
    # created_by: Optional[str] = None
    updated_time: Optional[int] = None
    # updated_by: Optional[str] = None
    is_deleted: Optional[int] = None

class BaseQueryReq(BaseTabelDto):
    sort: Optional[str] = Field(default="desc", description=" asc或 desc")
    orderby: Optional[str] = Field(default="created_time", description="根据什么字段排序")


class BasePageQueryReq(BaseQueryReq):
    page_number: Optional[int] = Field(default=1, description="第几页")
    page_size: Optional[int] = Field(default=12, description="一页多少条")


class BaseRenameReq(BaseModel):
    id: str
    name: str


class BasePageResp(BaseModel, Generic[T]):
    page_number: Optional[int]
    page_size: Optional[int]
    page_count: Optional[int]
    sort: Optional[str]
    orderby: Optional[str]
    count: Optional[int]
    data: Optional[List[T]]

    class Config:
        arbitrary_types_allowed = True
