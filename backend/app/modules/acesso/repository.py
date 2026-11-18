from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.acesso.models import Perfil, Usuario


def por_login(db: Session, login: str) -> Usuario | None:
    return db.scalar(select(Usuario).where(Usuario.login == login))


def perfis_por_nome(db: Session, nomes: list[str]) -> list[Perfil]:
    return list(db.scalars(select(Perfil).where(Perfil.nome.in_(nomes))))


def listar_stmt(ativo: bool | None = None, busca: str | None = None):
    stmt = select(Usuario).order_by(Usuario.nome)
    if ativo is not None:
        stmt = stmt.where(Usuario.ativo == ativo)
    if busca:
        stmt = stmt.where(Usuario.nome.ilike(f"%{busca}%") | Usuario.login.ilike(f"%{busca}%"))
    return stmt
