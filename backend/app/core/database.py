"""Conexão com o banco (SQLAlchemy 2.0) e sessão por requisição."""

from collections.abc import Iterator

from sqlalchemy import MetaData, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings

CONVENCAO_NOMES = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=CONVENCAO_NOMES)


def criar_engine(url: str) -> Engine:
    if url.startswith("sqlite"):
        # Usado apenas nos testes rápidos; o banco oficial é o PostgreSQL 16.
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool if ":memory:" in url else None,
        )
    return create_engine(url, pool_pre_ping=True)


engine = criar_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def configurar_engine(url: str) -> Engine:
    """Troca o banco em tempo de execução (usado pelos testes)."""
    global engine
    engine = criar_engine(url)
    SessionLocal.configure(bind=engine)
    return engine


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
