from contextvars import ContextVar
from contextvars import ContextVar
from typing import Optional, TypeVar, Generic, Type

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from entity import AsyncSessionLocal
from entity.user import User

# 1. 创建上下文变量存储当前会话
current_session: ContextVar[Optional[AsyncSession]] = ContextVar("current_session", default=None)

# 3. 中间件：管理请求生命周期和会话
async def db_session_middleware(request: Request, call_next):
    async with AsyncSessionLocal() as session:
        # 设置会话到上下文变量
        token = current_session.set(session)
        try:
            response = await call_next(request)
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            # 重置上下文变量
            current_session.reset(token)
    return response

# 4. 服务基类
T = TypeVar('T')

class BaseService(Generic[T]):
    model: Type[T] = None  # 子类必须指定模型

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
    async def get(cls, id: int) -> Optional[T]:
        """通用获取方法"""
        db = cls.get_db()
        return await db.get(cls.model, id)

# 5. 具体服务类
class UserService(BaseService[User]):
    model = User  # 指定模型
