"""Indicadores de absenteísmo, confirmação e recuperação de vagas (RF19, UC09).

Fórmulas:
- taxa_confirmacao   = agendamentos que receberam SIM / total de agendamentos do período
- taxa_absenteismo   = faltas / (realizados + faltas)
- taxa_recuperacao   = vagas preenchidas / vagas liberadas
- taxa_ocupacao      = horários ocupados ao final (ativos ou realizados) / horários distintos agendados
- tempo_medio_recuperacao_min = média entre a liberação e o preenchimento das vagas recuperadas
"""

from collections import Counter
from datetime import date, datetime, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.agenda.models import Agendamento, HistoricoStatusAgendamento, StatusAgendamento
from app.modules.recuperacao.models import OfertaVaga, StatusOferta, StatusVaga, VagaLiberada

S = StatusAgendamento
OCUPACAO_EFETIVA = {S.AGENDADO, S.AGUARDANDO_RESPOSTA, S.CONFIRMADO, S.REMARCACAO_SOLICITADA, S.REALIZADO}


def _taxa(parte: int, todo: int) -> float | None:
    return round(parte / todo, 4) if todo else None


def calcular(db: Session, inicio: date, fim: date, unidade_id: int | None = None,
             especialidade_id: int | None = None, profissional_id: int | None = None) -> dict:
    ini, fi = datetime.combine(inicio, time.min), datetime.combine(fim, time.max)

    def filtrar(stmt, modelo):
        stmt = stmt.where(modelo.data_hora >= ini, modelo.data_hora <= fi)
        if unidade_id:
            stmt = stmt.where(modelo.unidade_id == unidade_id)
        if especialidade_id:
            stmt = stmt.where(modelo.especialidade_id == especialidade_id)
        if profissional_id:
            stmt = stmt.where(modelo.profissional_id == profissional_id)
        return stmt

    ags = db.execute(filtrar(select(Agendamento.id, Agendamento.status, Agendamento.profissional_id,
                                    Agendamento.data_hora), Agendamento)).all()
    ids = [a.id for a in ags]
    por_status = Counter(a.status for a in ags)
    confirmados = remarcacoes = 0
    if ids:
        hist = db.execute(select(HistoricoStatusAgendamento.agendamento_id, HistoricoStatusAgendamento.status_novo)
                          .where(HistoricoStatusAgendamento.agendamento_id.in_(ids))).all()
        confirmados = len({h.agendamento_id for h in hist if h.status_novo == S.CONFIRMADO})
        remarcacoes = len({h.agendamento_id for h in hist if h.status_novo == S.REMARCACAO_SOLICITADA})

    horarios = {(a.profissional_id, a.data_hora) for a in ags}
    ocupados = {(a.profissional_id, a.data_hora) for a in ags if a.status in OCUPACAO_EFETIVA}

    vagas = db.scalars(filtrar(select(VagaLiberada), VagaLiberada)).all()
    vagas_status = Counter(v.status for v in vagas)
    tempos = [(v.data_preenchimento - v.data_liberacao).total_seconds() / 60
              for v in vagas if v.status == StatusVaga.PREENCHIDA and v.data_preenchimento]
    vaga_ids = [v.id for v in vagas]
    ofertas = Counter()
    if vaga_ids:
        ofertas = Counter(db.scalars(select(OfertaVaga.status).where(OfertaVaga.vaga_id.in_(vaga_ids))).all())

    total = len(ags)
    faltas, realizados = por_status[S.FALTA], por_status[S.REALIZADO]
    liberadas, recuperadas = len(vagas), vagas_status[StatusVaga.PREENCHIDA]
    return {
        "periodo": {"inicio": inicio, "fim": fim},
        "filtros": {"unidade_id": unidade_id, "especialidade_id": especialidade_id, "profissional_id": profissional_id},
        "agendamentos": {
            "total": total,
            "confirmados": confirmados,
            "cancelados": por_status[S.CANCELADO] + por_status[S.NAO_CONFIRMADO],
            "nao_respondidos": por_status[S.SEM_RESPOSTA],
            "remarcacoes_solicitadas": remarcacoes,
            "pendentes_de_resposta": por_status[S.AGENDADO] + por_status[S.AGUARDANDO_RESPOSTA],
            "realizados": realizados,
            "faltas": faltas,
            "por_status": {s.value: por_status[s] for s in S},
        },
        "vagas": {
            "liberadas": liberadas,
            "recuperadas": recuperadas,
            "em_oferta": vagas_status[StatusVaga.EM_OFERTA],
            "sem_elegiveis": vagas_status[StatusVaga.SEM_ELEGIVEIS],
            "encerradas": vagas_status[StatusVaga.ENCERRADA],
            "tempo_medio_recuperacao_min": round(sum(tempos) / len(tempos), 1) if tempos else None,
        },
        "ofertas": {s.value: ofertas[s] for s in StatusOferta},
        "taxas": {
            "taxa_confirmacao": _taxa(confirmados, total),
            "taxa_absenteismo": _taxa(faltas, realizados + faltas),
            "taxa_recuperacao": _taxa(recuperadas, liberadas),
            "taxa_ocupacao": _taxa(len(ocupados), len(horarios)),
        },
    }
