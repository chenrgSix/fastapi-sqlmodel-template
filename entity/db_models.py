from sqlmodel import SQLModel

from entity import DbBaseModel, engine


# 初始化数据库表（异步执行）
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


class User(DbBaseModel, table=True):
    __tablename__ = "user"  # 可以显式指定数据库表名，默认实体名转小写
    username: str
    password: str
