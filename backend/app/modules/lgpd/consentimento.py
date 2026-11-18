"""Registro do histórico de consentimento, usado por cadastros e pelo módulo LGPD (RF21, RN17)."""

from sqlalchemy.orm import Session

from app.core.relogio import agora
from app.modules.cadastros.models import Contato
from app.modules.lgpd.models import AcaoConsentimento, HistoricoConsentimento


def registrar_historico(
    db: Session, contato: Contato, acao: AcaoConsentimento, origem: str, detalhes: dict | None = None
) -> HistoricoConsentimento:
    h = HistoricoConsentimento(
        paciente_id=contato.paciente_id,
        contato_id=contato.id,
        acao=acao,
        data_hora=agora(),
        origem=origem,
        detalhes=detalhes,
    )
    db.add(h)
    return h


def autorizar_contato(db: Session, contato: Contato, origem: str, preferencias: dict | None = None) -> None:
    contato.autorizado = True
    contato.data_autorizacao = agora()
    contato.data_revogacao = None
    contato.origem_alteracao = origem
    if preferencias is not None:
        contato.preferencias = preferencias
    registrar_historico(db, contato, AcaoConsentimento.AUTORIZOU, origem, {"preferencias": preferencias})


def revogar_contato(db: Session, contato: Contato, origem: str, motivo: str | None = None) -> None:
    contato.autorizado = False
    contato.data_revogacao = agora()
    contato.origem_alteracao = origem
    registrar_historico(db, contato, AcaoConsentimento.REVOGOU, origem, {"motivo": motivo} if motivo else None)
