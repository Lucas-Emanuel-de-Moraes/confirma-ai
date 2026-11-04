"""Enfileiramento (outbox) e envio de mensagens com retentativas e idempotência (RNF11, RNF12, RN16).

Todo envio passa por este ponto único: a autorização de contato é verificada ao enfileirar
e de novo no momento do envio, de modo que uma revogação tem efeito imediato mesmo para
mensagens que já estavam na fila (seção 11.8).
"""

import logging
import secrets
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import eventos, metricas
from app.core.config import settings
from app.core.relogio import agora
from app.modules.auditoria import service as auditoria
from app.modules.cadastros.models import Contato, Paciente
from app.modules.notificacao.gateway import MensagemSaida, obter_gateway
from app.modules.notificacao.models import (
    Mensagem,
    OutboxEvento,
    StatusMensagem,
    StatusOutbox,
    TipoMensagem,
)

log = logging.getLogger("confirma_ai.notificacao")

OPCOES_LEMBRETE = [("SIM", "Sim, confirmo"), ("NAO", "Não vou"), ("REMARCAR", "Remarcar")]
OPCOES_OFERTA = [("ACEITAR", "Aceitar vaga"), ("RECUSAR", "Recusar")]


def opcoes_por_tipo(tipo: TipoMensagem) -> list[tuple[str, str]]:
    return {TipoMensagem.LEMBRETE_CONFIRMACAO: OPCOES_LEMBRETE, TipoMensagem.OFERTA_ENCAIXE: OPCOES_OFERTA}.get(tipo, [])


def gerar_identificador() -> str:
    """Identificador aleatório e não adivinhável (RNF19)."""
    return secrets.token_urlsafe(16)


def enfileirar(
    db: Session,
    *,
    tipo: TipoMensagem,
    paciente: Paciente,
    conteudo: str,
    chave_idempotencia: str,
    agendamento_id: int | None = None,
    oferta_id: int | None = None,
    expira_em: datetime | None = None,
    max_tentativas: int = 3,
    com_identificador: bool = True,
) -> Mensagem:
    """Grava a mensagem e o evento de outbox na mesma transação da regra de negócio."""
    existente = db.scalar(select(OutboxEvento).where(OutboxEvento.chave_idempotencia == chave_idempotencia))
    if existente is not None:
        return existente.mensagem  # mesma chave = mesma mensagem (sem duplicar)

    contato: Contato | None = paciente.contato_principal
    if contato is None:
        raise ValueError("Paciente sem contato cadastrado.")
    mensagem = Mensagem(
        tipo=tipo,
        conteudo=conteudo,
        identificador_unico=gerar_identificador() if com_identificador else None,
        status=StatusMensagem.PENDENTE,
        tentativas=0,
        data_criacao=agora(),
        data_expiracao=expira_em,
        paciente_id=paciente.id,
        contato_id=contato.id,
        agendamento_id=agendamento_id,
        oferta_id=oferta_id,
    )
    db.add(mensagem)
    if not paciente.pode_receber_mensagem:
        # RN16: sem autorização ativa nada é enviado; o registro fica para auditoria.
        mensagem.status = StatusMensagem.BLOQUEADA
        mensagem.motivo = "Contato não autorizado ou paciente inativo"
        db.flush()
        auditoria.registrar(db, "MENSAGEM_BLOQUEADA", "mensagem", mensagem.id, detalhes={"tipo": tipo.value})
        return mensagem
    db.flush()
    db.add(OutboxEvento(
        mensagem_id=mensagem.id,
        chave_idempotencia=chave_idempotencia,
        status=StatusOutbox.PENDENTE,
        tentativas=0,
        max_tentativas=max_tentativas,
        proxima_tentativa=agora(),
        criado_em=agora(),
    ))
    db.flush()
    return mensagem


def cancelar_pendentes_do_paciente(db: Session, paciente_id: int, motivo: str) -> int:
    eventos_pendentes = db.scalars(
        select(OutboxEvento).join(Mensagem).where(
            Mensagem.paciente_id == paciente_id, OutboxEvento.status == StatusOutbox.PENDENTE
        )
    ).all()
    for ev in eventos_pendentes:
        ev.status = StatusOutbox.CANCELADO
        ev.processado_em = agora()
        ev.ultimo_erro = motivo
        ev.mensagem.status = StatusMensagem.CANCELADA
        ev.mensagem.motivo = motivo
    return len(eventos_pendentes)


def cancelar_mensagem(db: Session, mensagem: Mensagem, motivo: str, status=StatusMensagem.CANCELADA) -> None:
    mensagem.status = status
    mensagem.motivo = motivo
    ev = db.scalar(select(OutboxEvento).where(OutboxEvento.mensagem_id == mensagem.id))
    if ev is not None and ev.status == StatusOutbox.PENDENTE:
        ev.status = StatusOutbox.CANCELADO
        ev.processado_em = agora()


def _falha(db: Session, ev: OutboxEvento, erro: str, temporario: bool) -> None:
    m = ev.mensagem
    ev.tentativas += 1
    m.tentativas = ev.tentativas
    ev.ultimo_erro = (erro or "")[:300]
    definitiva = (not temporario) or ev.tentativas >= ev.max_tentativas
    metricas.MENSAGENS_FALHAS.labels(m.tipo.value, str(definitiva).lower()).inc()
    if definitiva:
        ev.status = StatusOutbox.FALHA_DEFINITIVA
        ev.processado_em = agora()
        m.status = StatusMensagem.FALHA
        m.motivo = "Falha definitiva de contato"
        auditoria.registrar(db, "MENSAGEM_FALHA_DEFINITIVA", "mensagem", m.id,
                            detalhes={"tipo": m.tipo.value, "tentativas": ev.tentativas})
        db.flush()
        eventos.publicar(eventos.MENSAGEM_NAO_ENTREGUE, db=db, mensagem=m)
    else:
        # Retentativa espaçada: 30 s, 60 s, 120 s... (RNF12)
        ev.proxima_tentativa = agora() + timedelta(seconds=settings.RETENTATIVA_BASE_SEG * 2 ** (ev.tentativas - 1))


def _processar_evento(db: Session, evento_id: int) -> str:
    stmt = select(OutboxEvento).where(OutboxEvento.id == evento_id, OutboxEvento.status == StatusOutbox.PENDENTE)
    ev = db.scalar(stmt.with_for_update(skip_locked=True, of=OutboxEvento))
    if ev is None:
        return "ignorado"  # já processado por outro worker
    m = ev.mensagem
    paciente = db.get(Paciente, m.paciente_id)
    contato = db.get(Contato, m.contato_id)

    # Consentimento verificado no momento do envio (RN16)
    if not (paciente and paciente.pode_receber_mensagem and contato and contato.autorizado):
        ev.status = StatusOutbox.CANCELADO
        ev.processado_em = agora()
        m.status = StatusMensagem.CANCELADA
        m.motivo = "Autorização revogada ou paciente inativo antes do envio"
        auditoria.registrar(db, "MENSAGEM_CANCELADA_SEM_AUTORIZACAO", "mensagem", m.id)
        db.flush()
        eventos.publicar(eventos.MENSAGEM_NAO_ENTREGUE, db=db, mensagem=m)
        return "cancelado"
    if m.data_expiracao and m.data_expiracao <= agora():
        ev.status = StatusOutbox.CANCELADO
        ev.processado_em = agora()
        m.status = StatusMensagem.EXPIRADA
        m.motivo = "Prazo vencido antes do envio"
        db.flush()
        eventos.publicar(eventos.MENSAGEM_NAO_ENTREGUE, db=db, mensagem=m)
        return "expirado"

    resultado = obter_gateway().enviar(MensagemSaida(
        destino=contato.valor,
        texto=m.conteudo,
        tipo=m.tipo.value,
        chave_idempotencia=ev.chave_idempotencia,
        identificador=m.identificador_unico,
        opcoes=opcoes_por_tipo(m.tipo),
        parametros_modelo=[m.conteudo],
    ))
    if resultado.sucesso:
        ev.tentativas += 1
        ev.status = StatusOutbox.ENVIADO
        ev.processado_em = agora()
        m.tentativas = ev.tentativas
        m.status = StatusMensagem.ENVIADA
        m.data_envio = agora()
        m.id_externo = resultado.id_externo
        metricas.MENSAGENS_ENVIADAS.labels(m.tipo.value).inc()
        auditoria.registrar(db, "MENSAGEM_ENVIADA", "mensagem", m.id, detalhes={"tipo": m.tipo.value})
        db.flush()
        eventos.publicar(eventos.MENSAGEM_ENVIADA, db=db, mensagem=m)
        return "enviado"
    _falha(db, ev, resultado.erro or "erro desconhecido", resultado.temporario)
    return "falha"


def processar_outbox(db: Session, limite: int = 50) -> dict[str, int]:
    """Envia as mensagens pendentes cujo horário de tentativa já chegou. Cada envio tem sua transação."""
    ids = db.scalars(
        select(OutboxEvento.id)
        .where(OutboxEvento.status == StatusOutbox.PENDENTE, OutboxEvento.proxima_tentativa <= agora())
        .order_by(OutboxEvento.proxima_tentativa, OutboxEvento.id)
        .limit(limite)
    ).all()
    db.rollback()
    contagem: dict[str, int] = {}
    for evento_id in ids:
        try:
            r = _processar_evento(db, evento_id)
            db.commit()
        except Exception:  # noqa: BLE001 – uma falha não pode travar a fila inteira
            db.rollback()
            log.exception("Erro ao processar evento de outbox %s", evento_id)
            r = "erro"
        contagem[r] = contagem.get(r, 0) + 1
    return contagem
