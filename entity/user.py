from entity.base_entity import DbBaseModel


class User(DbBaseModel,table=True):
    __tablename__ = "user"  # 可以显式指定数据库表名，默认实体名转小写
    username: str
    password: str
