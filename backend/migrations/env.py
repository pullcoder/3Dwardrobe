"""Settings와 동일한 DB에 버전 고정 스키마 변경을 적용한다."""

from alembic import context
from sqlalchemy import create_engine, pool

from app.core.config import Settings
from app.models import Base

config = context.config
target_metadata = Base.metadata
url = Settings().database_url

if context.is_offline_mode():
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
