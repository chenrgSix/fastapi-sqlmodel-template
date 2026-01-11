import functools
import inspect
from contextlib import asynccontextmanager
from typing import Any, ParamSpec, TypeVar, Callable

from sqlalchemy import Executable, Result, and_, Select, Delete, Update
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.sql.selectable import Subquery

from common.constant import Constant
from common.global_enums import IsDelete
from config import settings

P = ParamSpec('P')
T = TypeVar('T')

engine = create_async_engine(settings.database_url, echo=False,  # 打印SQL日志（生产环境建议关闭）
                             pool_size=10,  # 连接池大小
                             max_overflow=20,  # 最大溢出连接数
                             pool_recycle=3600,  # 连接回收时间（秒），解决MySQL超时断开问题【4†source】【5†source】
                             )


# 创建异步会话工厂


class EnhanceAsyncSession(AsyncSession):

    def _add_logical_delete_condition(self, statement: Select) -> Select:
        """
        为 Select 语句添加逻辑删除条件
        支持递归处理 fastapi-pagination 生成的子查询包装
        """
        # 特殊处理：如果当前查询只有一个子查询，直接修改其内部元素
        # 这样可以避免产生重复的别名
        if len(statement.froms) == 1 and isinstance(statement.froms[0], Subquery):
            subquery = statement.froms[0]
            # 递归处理子查询内部
            processed_inner = self._add_logical_delete_condition(subquery.element)
            # 如果内部有修改，直接替换 subquery 的 element
            if processed_inner is not subquery.element:
                subquery.element = processed_inner
            return statement

        # 处理当前层的表
        delete_condition = None
        delete_field = Constant.LOGICAL_DELETE_FIELD

        for from_obj in statement.froms:
            # 跳过子查询（因为会通过上面的逻辑递归处理）
            if isinstance(from_obj, Subquery):
                continue

            # 只处理 Table 对象
            if hasattr(from_obj, 'columns') and delete_field in from_obj.columns:
                # 使用表对象上的列
                condition = from_obj.columns[delete_field] == IsDelete.NO_DELETE

                if delete_condition is None:
                    delete_condition = condition
                else:
                    delete_condition = and_(delete_condition, condition)

        # 如果有条件，则应用到当前 statement
        if delete_condition is not None:
            existing_condition = statement.whereclause
            if existing_condition is not None:
                new_condition = and_(existing_condition, delete_condition)
            else:
                new_condition = delete_condition

            statement = statement.where(new_condition)

        return statement

    async def scalar(self, statement: Executable, params=None, *, execution_options=None, bind_arguments=None,
                     **kw: Any, ):
        sig = inspect.signature(super().scalar)
        if execution_options is None:
            default_execution_options = sig.parameters['execution_options'].default
            execution_options = default_execution_options

        # 只对 Select 语句添加逻辑删除条件
        if isinstance(statement, Select):
            statement = self._add_logical_delete_condition(statement)

        return await super().scalar(statement, params, execution_options=execution_options,
                                    bind_arguments=bind_arguments, **kw)

    async def execute(self, statement: Executable, params=None, *, execution_options=None, bind_arguments=None,
                      **kw: Any, ) -> Result[Any]:
        sig = inspect.signature(super().execute)
        if execution_options is None:
            default_execution_options = sig.parameters['execution_options'].default
            execution_options = default_execution_options

        if isinstance(statement, Select):
            statement = self._add_logical_delete_condition(statement)

        if isinstance(statement, Delete):
            skip_soft_delete = execution_options and execution_options.get("skip_soft_delete", False)

            if not skip_soft_delete:
                table = statement.table

                if hasattr(table, 'columns') and Constant.LOGICAL_DELETE_FIELD in table.columns:
                    update_stmt = (Update(table).where(statement.whereclause).values(
                        **{Constant.LOGICAL_DELETE_FIELD: IsDelete.DELETE}))

                    if statement._returning:
                        update_stmt = update_stmt.returning(*statement._returning)

                    return await super().execute(update_stmt, params=params, execution_options=execution_options,
                                                 bind_arguments=bind_arguments, **kw)

        result = await super().execute(statement, params=params, execution_options=execution_options,
                                       bind_arguments=bind_arguments, **kw, )
        return result

    def delete(self, instance):
        from sqlalchemy import inspect as sqlalchemy_inspect

        if hasattr(instance, Constant.LOGICAL_DELETE_FIELD):
            setattr(instance, Constant.LOGICAL_DELETE_FIELD, IsDelete.DELETE)

            insp = sqlalchemy_inspect(instance)
            if insp.detached or insp.transient:
                self.add(instance)
        else:
            super().delete(instance)


AsyncSessionLocal = async_sessionmaker(bind=engine, class_=EnhanceAsyncSession, expire_on_commit=False,  # 提交后不使对象过期
                                       autoflush=False  # 禁用自动刷新
                                       )


# 获取数据库session的独立方法
@asynccontextmanager
async def get_db_session():
    """获取数据库session的上下文管理器"""
    async with AsyncSessionLocal() as session:
        async with session.begin():
            yield session


def with_db_session(session_param_name: str = "session"):
    """
    一个装饰器，用于为异步函数自动注入数据库会话。

    Args:
        session_param_name: 被装饰函数中，用于接收会话的参数名，默认为 'session'。
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        # 确保只装饰异步函数
        if not inspect.iscoroutinefunction(func):
            raise TypeError("`with_db_session` can only be used on async functions.")

        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # 如果调用时已经手动传了 session，就直接用
            if session_param_name in kwargs:
                return await func(*args, **kwargs)

            # 否则，创建一个新 session 并注入
            async with get_db_session() as session:
                kwargs[session_param_name] = session
                return await func(*args, **kwargs)

        return wrapper

    return decorator


# 关闭引擎
async def close_engine():
    await engine.dispose()
