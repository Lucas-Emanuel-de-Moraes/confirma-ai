from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

usuario_perfil = Table(
    "usuario_perfil",
    Base.metadata,
    Column("usuario_id", ForeignKey("usuario.id", ondelete="CASCADE"), primary_key=True),
    Column("perfil_id", ForeignKey("perfil.id", ondelete="CASCADE"), primary_key=True),
)


class Perfil(Base):
    __tablename__ = "perfil"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(40), unique=True)
    permissoes: Mapped[list[str]] = mapped_column(JSON, default=list)

    def possui(self, permissao: str) -> bool:
        return "*" in (self.permissoes or []) or permissao in (self.permissoes or [])


class Usuario(Base):
    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    login: Mapped[str] = mapped_column(String(60), unique=True)
    senha_hash: Mapped[str] = mapped_column(String(200))
    mfa_habilitado: Mapped[bool] = mapped_column(Boolean, default=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    # Lotação opcional: restringe a visualização à unidade (segregação, seção 5.3)
    unidade_id: Mapped[int | None] = mapped_column(ForeignKey("unidade_saude.id"))
    criado_em: Mapped[datetime] = mapped_column(DateTime)

    perfis: Mapped[list[Perfil]] = relationship(secondary=usuario_perfil, lazy="selectin")

    def possui_permissao(self, permissao: str) -> bool:
        return any(p.possui(permissao) for p in self.perfis)

    @property
    def eh_admin(self) -> bool:
        return any("*" in (p.permissoes or []) for p in self.perfis)

    @property
    def nomes_perfis(self) -> list[str]:
        return [p.nome for p in self.perfis]
