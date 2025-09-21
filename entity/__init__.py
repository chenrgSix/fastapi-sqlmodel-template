import asyncio
import inspect
from typing import Any

from sqlalchemy import Executable, Result, Select, Delete, Update, column, and_
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlmodel import SQLModel

from common.constant import Constant
from common.global_enums import IsDelete
from config import settings
from entity.base_entity import DbBaseModel

engine = create_async_engine(
    settings.database_url,
    echo=False,  # 打印SQL日志（生产环境建议关闭）
    pool_size=10,  # 连接池大小
    max_overflow=20,  # 最大溢出连接数
    pool_recycle=3600,  # 连接回收时间（秒），解决MySQL超时断开问题【4†source】【5†source】
)


# 创建异步会话工厂
class EnhanceAsyncSession(AsyncSession):
    async def scalar(self, statement: Executable,
                     params=None,
                     *,
                     execution_options=None,
                     bind_arguments=None,
                     **kw: Any, ):

        sig = inspect.signature(super().scalar)
        if execution_options is None:
            default_execution_options = sig.parameters['execution_options'].default
            execution_options = default_execution_options
        delete_condition = column(Constant.LOGICAL_DELETE_FIELD) == IsDelete.NO_DELETE
        existing_condition = statement.whereclause
        # 组合条件
        if existing_condition is not None:
            # 使用and_组合现有条件和逻辑删除条件
            new_condition = and_(existing_condition, delete_condition)
        else:
            new_condition = delete_condition
            # 应用新条件（创建新的Select对象）
        statement = statement.where(new_condition)
        return await super().scalar(statement, params, execution_options=execution_options,
                                    bind_arguments=bind_arguments, **kw)

    async def execute(
            self,
            statement: Executable,
            params=None,
            *,
            execution_options=None,
            bind_arguments=None,
            **kw: Any,
    ) -> Result[Any]:
        sig = inspect.signature(super().execute)
        if execution_options is None:
            default_execution_options = sig.parameters['execution_options'].default
            execution_options = default_execution_options
        print("type(statement):{}", type(statement))
        if isinstance(statement, Select):
            print("这是查询语句，过滤逻辑删除")
            delete_condition = column(Constant.LOGICAL_DELETE_FIELD) == IsDelete.NO_DELETE
            # 获取现有条件
            existing_condition = statement.whereclause
            # 组合条件
            if existing_condition is not None:
                # 使用and_组合现有条件和逻辑删除条件
                new_condition = and_(existing_condition, delete_condition)
            else:
                new_condition = delete_condition
            # 应用新条件（创建新的Select对象）
            statement = statement.where(new_condition)
        if isinstance(statement, Delete):
            # 检查是否跳过软删除（通过execution_options控制）
            skip_soft_delete = execution_options and execution_options.get("skip_soft_delete", False)

            if not skip_soft_delete:
                # 获取表对象
                table = statement.table

                # 构建更新语句
                update_stmt = (
                    Update(table)
                    .where(statement.whereclause)  # 保留原删除条件
                    .values(**{Constant.LOGICAL_DELETE_FIELD: IsDelete.DELETE})  # 设置软删除标记
                )

                # 如果原删除语句有RETURNING子句，也添加到更新语句中
                if statement._returning:
                    update_stmt = update_stmt.returning(*statement._returning)
                # 执行更新语句
                return await super().execute(
                    update_stmt,
                    params=params,
                    execution_options=execution_options,
                    bind_arguments=bind_arguments,
                    **kw
                )
        result = await super().execute(
            statement,
            params=params,
            execution_options=execution_options,
            bind_arguments=bind_arguments,
            **kw,
        )
        return result

    # 重写delete方法处理单个对象删除
    def delete(self, instance):
        from sqlalchemy import inspect
        # 检查是否有逻辑删除属性
        if hasattr(instance, Constant.LOGICAL_DELETE_FIELD):
            # 设置软删除标记
            instance.__setattr__(Constant.LOGICAL_DELETE_FIELD, IsDelete.DELETE)
            # 确保对象在会话中（如果已分离则重新关联）
            # 检查对象状态
            insp = inspect(instance)
            if insp.detached:
                # 如果对象是分离的，则重新加入会话
                self.add(instance)
            elif insp.transient:
                # 如果是瞬态对象，也添加到会话
                self.add(instance)

            # 标记对象为已修改（触发更新）
            # self.expire(instance, [Constant.LOGICAL_DELETE_FIELD])
        else:
            # 如果没有逻辑删除属性，执行标准删除
            super().delete(instance)


AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=EnhanceAsyncSession,
    expire_on_commit=False,  # 提交后不使对象过期
    autoflush=False  # 禁用自动刷新
)


# 关闭引擎
async def close_engine():
    await engine.dispose()


# 初始化数据库表（异步执行）
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


if __name__ == '__main__':
    import user


    async def main():
        try:
            await init_db()
        finally:
            await close_engine()  # 确保引擎关闭


    asyncio.run(main())
