from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, event
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LogAuditoria(Base):
    """Registro de auditoria somente-inserção (RN12, RN17, RNF07).

    A aplicação nunca altera nem apaga linhas desta tabela; no PostgreSQL um gatilho criado
    pela migration também bloqueia UPDATE e DELETE.
    """

    __tablename__ = "log_auditoria"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    acao: Mapped[str] = mapped_column(String(60))
    entidade: Mapped[str] = mapped_column(String(60))
    entidade_id: Mapped[str | None] = mapped_column(String(40))
    data_hora: Mapped[datetime] = mapped_column(DateTime)
    origem: Mapped[str] = mapped_column(String(80))
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))
    detalhes: Mapped[dict | None] = mapped_column(JSON)

    __table_args__ = (
        Index("ix_log_auditoria_entidade", "entidade", "entidade_id"),
        Index("ix_log_auditoria_data_hora", "data_hora"),
    )


@event.listens_for(LogAuditoria, "before_update")
def _bloquear_update(*_):
    raise PermissionError("LogAuditoria é somente inserção (RN12).")


@event.listens_for(LogAuditoria, "before_delete")
def _bloquear_delete(*_):
    raise PermissionError("LogAuditoria é somente inserção (RN12).")
