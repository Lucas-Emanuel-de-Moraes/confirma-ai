"""Serviço único de auditoria usado por todos os módulos (PB09, RN12, RNF07).

Grava ação, entidade, data/hora e origem. Os detalhes devem conter apenas identificadores e
informações operacionais – nunca nome completo, telefone completo ou dado clínico.
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.paginacao import ParamsPaginacao, paginar
from app.core.relogio import agora
from app.modules.auditoria.models import LogAuditoria

ORIGEM_SISTEMA = "sistema"


def origem_usuario(usuario) -> str:
    return f"usuario:{usuario.id}" if usuario is not None else ORIGEM_SISTEMA


def registrar(
    db: Session,
    acao: str,
    entidade: str,
    entidade_id: int | str | None = None,
    origem: str = ORIGEM_SISTEMA,
    usuario_id: int | None = None,
    detalhes: dict | None = None,
) -> LogAuditoria:
    log = LogAuditoria(
        acao=acao,
        entidade=entidade,
        entidade_id=str(entidade_id) if entidade_id is not None else None,
        data_hora=agora(),
        origem=origem,
        usuario_id=usuario_id,
        detalhes=detalhes,
    )
    db.add(log)
    return log


def listar(
    db: Session,
    params: ParamsPaginacao,
    entidade: str | None = None,
    entidade_id: str | None = None,
    acao: str | None = None,
    inicio: datetime | None = None,
    fim: datetime | None = None,
) -> dict:
    stmt = select(LogAuditoria).order_by(LogAuditoria.id.desc())
    if entidade:
        stmt = stmt.where(LogAuditoria.entidade == entidade)
    if entidade_id:
        stmt = stmt.where(LogAuditoria.entidade_id == entidade_id)
    if acao:
        stmt = stmt.where(LogAuditoria.acao == acao)
    if inicio:
        stmt = stmt.where(LogAuditoria.data_hora >= inicio)
    if fim:
        stmt = stmt.where(LogAuditoria.data_hora <= fim)
    return paginar(db, stmt, params)
