"""Tarefas periódicas (APScheduler) e endpoint para dispará-las manualmente.

- outbox ............. envia mensagens pendentes com retentativas (a cada OUTBOX_INTERVALO_SEG)
- lembretes .......... enfileira lembretes conforme a antecedência configurada (UC03)
- expirar-respostas .. marca SEM_RESPOSTA e libera a vaga quando o prazo vence (RF11)
- expirar-ofertas .... expira reservas vencidas e oferece ao próximo da fila (RN11, RF16)
- retencao ........... eliminação/anonimização diária às 03:00 (RF23)
"""

import logging
from collections.abc import Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.erros import NaoEncontrado
from app.modules.acesso import permissoes as P
from app.modules.acesso.dependencias import exigir
from app.modules.acesso.models import Usuario
from app.modules.confirmacao import service as confirmacao
from app.modules.lgpd import service as lgpd
from app.modules.notificacao import service as notificacao
from app.modules.recuperacao import service as recuperacao

log = logging.getLogger("confirma_ai.tarefas")

TAREFAS: dict[str, Callable[[Session], dict]] = {
    "lembretes": confirmacao.enviar_lembretes,
    "outbox": notificacao.processar_outbox,
    "expirar-respostas": confirmacao.expirar_sem_resposta,
    "expirar-ofertas": recuperacao.expirar_ofertas,
    "retencao": lgpd.executar_retencao,
}


def executar(nome: str) -> dict:
    with SessionLocal() as db:
        if nome == "ciclo":
            # Atalho para testes manuais: roda o fluxo completo uma vez, na ordem natural.
            return {n: TAREFAS[n](db) for n in ("lembretes", "outbox", "expirar-respostas", "expirar-ofertas")} | {
                "outbox (2ª passada)": TAREFAS["outbox"](db)
            }
        return TAREFAS[nome](db)


def _job(nome: str) -> Callable[[], None]:
    def rodar() -> None:
        try:
            resultado = executar(nome)
            if any(v for v in resultado.values() if isinstance(v, int)):
                log.info("Tarefa %s: %s", nome, resultado)
        except Exception:  # noqa: BLE001
            log.exception("Falha na tarefa %s", nome)

    return rodar


agendador: BackgroundScheduler | None = None


def iniciar() -> None:
    global agendador
    agendador = BackgroundScheduler(timezone=settings.FUSO_HORARIO)
    comum = {"max_instances": 1, "coalesce": True, "replace_existing": True}
    agendador.add_job(_job("outbox"), IntervalTrigger(seconds=settings.OUTBOX_INTERVALO_SEG), id="outbox", **comum)
    for nome in ("lembretes", "expirar-respostas", "expirar-ofertas"):
        agendador.add_job(_job(nome), IntervalTrigger(seconds=settings.TAREFAS_INTERVALO_SEG), id=nome, **comum)
    agendador.add_job(_job("retencao"), CronTrigger(hour=3, minute=0), id="retencao", **comum)
    agendador.start()
    log.info("Agendador iniciado (%s tarefas).", len(agendador.get_jobs()))


def parar() -> None:
    if agendador is not None and agendador.running:
        agendador.shutdown(wait=False)


router = APIRouter(prefix="/tarefas", tags=["Tarefas agendadas"])


@router.post("/{nome}", summary="Executa uma tarefa agora (lembretes, outbox, expirar-respostas, expirar-ofertas, "
                                "retencao ou ciclo)")
def executar_agora(nome: str, _: Usuario = Depends(exigir(P.TAREFAS_EXECUTAR))):
    if nome != "ciclo" and nome not in TAREFAS:
        raise NaoEncontrado(f"Tarefa desconhecida. Use: {', '.join([*TAREFAS, 'ciclo'])}.")
    return executar(nome)
