from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from core.global_context import current_session
from entity import AsyncSessionLocal

class DbSessionMiddleWare(BaseHTTPMiddleware):
    async def dispatch(self,request: Request, call_next):
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
                # 无论成功与否，都必须关闭会话
                await session.close()
        return response