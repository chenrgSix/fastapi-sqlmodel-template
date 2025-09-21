from typing import Optional

from pydantic import Field

from entity.dto.base import BasePageQueryReq


class UserQueryPageReq(BasePageQueryReq):
    username: Optional[str]= Field(default=None,description=" asc或 desc")