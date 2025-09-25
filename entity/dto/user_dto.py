from typing import Optional

from pydantic import Field

from entity.dto.base import BasePageQueryReq, BaseQueryReq


class UserQueryReq(BaseQueryReq):
    username: Optional[str]= Field(default=None,description="名称")


class UserQueryPageReq(UserQueryReq, BasePageQueryReq):
    pass
