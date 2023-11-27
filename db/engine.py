from sqlalchemy import URL
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine, async_scoped_session
from typing import Union

from sqlalchemy.orm import sessionmaker


def create_db_async_engine(url: Union[URL, str]) -> AsyncEngine:
    return create_async_engine(
        url=url,
        echo=True,
        pool_pre_ping=True,
    )


async def proceed_schema(engine: AsyncEngine, metadata) -> None:
    async with engine.connect() as session:
        try:
            await session.run_sync(metadata.create_all)
        except Exception as e:
            print("Error creating tables:", e)


def get_session_maker(engine: AsyncEngine):
    return sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
