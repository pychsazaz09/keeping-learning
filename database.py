from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker,AsyncSession

DEFAULT_URL="postgresql+asyncpg://postgres:interview123@localhost:5432/interview_agent"

engine=create_async_engine(
    url=DEFAULT_URL,
    echo=True,
    pool_size=10,
    max_overflow=20
)

AsyncSessionLocal=async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
