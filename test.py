import asyncio

from sqlalchemy import delete
from sqlmodel import select

from entity import AsyncSessionLocal, close_engine
from entity.user import User


async def add():
    add_list = []
    add_list.append(User(id="a460359e960311f09677c922f415afd9", username="u1", password="密码"))
    add_list.append(User(id="a460416a960311f09677c922f415afd9", username="u2", password="密码"))
    add_list.append(User(id="a46042be960311f09677c922f415afd9", username="u3", password="密码"))
    # session = get_db_session()
    async with AsyncSessionLocal() as session:
        for user in add_list:
            session.add(user)
        await session.commit()
        await close_engine()
        print("完成")


async def remove():
    add_list = []
    add_list.append(User(id="a460359e960311f09677c922f415afd9", username="u1", password="密码"))
    add_list.append(User(id="a460416a960311f09677c922f415afd9", username="u2", password="密码"))
    add_list.append(User(id="a46042be960311f09677c922f415afd9", username="u3", password="密码"))
    async with AsyncSessionLocal() as session:
        for i in add_list:
            delete_sql = delete(User).where(User.id == i.id)
            await session.execute(delete_sql)
        await session.commit()
        await close_engine()
    print("======================删除完成=================")
async def remove_one():
    add_list = []
    add_list.append(User(id="a460359e960311f09677c922f415afd9", username="u1", password="密码"))
    add_list.append(User(id="a460416a960311f09677c922f415afd9", username="u2", password="密码"))
    add_list.append(User(id="a46042be960311f09677c922f415afd9", username="u3", password="密码"))
    async with AsyncSessionLocal() as session:
        # for i in add_list:
        #     delete_sql = delete(User).where(User.id == i.id)
        user=await session.execute(select(User))
        user = user.scalars().first()
        session.delete(user)
        await session.commit()
        await close_engine()
    print("======================删除完成=================")
async def get_all():
    async with AsyncSessionLocal() as session:
        sql = select(User)
        result = await session.execute(sql)
        print(result.scalars().all())
        await session.commit()
        await close_engine()
    print("====================get_all==================")
def test(aa="ddd"):
    print("aa=", aa)
if __name__ == "__main__":
    # asyncio.run(add())
    asyncio.run(get_all())
    # asyncio.run(remove_one())
    asyncio.run(remove())
    asyncio.run(get_all())
    # test(None)
