from contextvars import ContextVar
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

current_session: ContextVar[Optional[AsyncSession]] = ContextVar("current_session", default=None)
