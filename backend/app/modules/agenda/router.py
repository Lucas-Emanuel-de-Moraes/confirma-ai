from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.paginacao import Pagina, ParamsPaginacao, params_paginacao
from app.modules.acesso import permissoes as P
from app.modules.acesso.dependencias import exigir, unidade_permitida
from app.modules.acesso.models import Usuario
from app.modules.agenda import service
from app.modules.agenda.models import StatusAgendamento
from app.modules.agenda.schemas import (
    AgendamentoCriar,
    AgendamentoSaida,
    CancelamentoEntrada,
    ComparecimentoEntrada,
    EventoHistorico,
)
from app.modules.auditoria import service as auditoria

router = APIRouter(prefix="/agendamentos", tags=["Agenda"])


@router.post("", response_model=AgendamentoSaida, status_code=201, summary="Registra agendamento (UC02)")
def criar(dados: AgendamentoCriar, db: Session = Depends(get_db), u: Usuario = Depends(exigir(P.AGENDA_ESCREVER))):
    return service.criar(db, dados, auditoria.origem_usuario(u), u.id)


@router.get("", response_model=Pagina[AgendamentoSaida], summary="Agenda com filtros (RF04)")
def listar(
    unidade_id: int | None = None,
    data: date | None = Query(None, description="Dia (AAAA-MM-DD)"),
    inicio: datetime | None = None,
    fim: datetime | None = None,
    especialidade_id: int | None = None,
    profissional_id: int | None = None,
    status: list[StatusAgendamento] | None = Query(None),
    paciente_id: int | None = None,
    busca: str | None = Query(None, description="Nome do paciente ou número do agendamento"),
    params: ParamsPaginacao = Depends(params_paginacao),
    db: Session = Depends(get_db),
    u: Usuario = Depends(exigir(P.AGENDA_LER)),
):
    unidade_id = unidade_permitida(u, unidade_id)
    return service.listar(db, params, unidade_id, data, inicio, fim, especialidade_id, profissional_id, status,
                          paciente_id, busca)


@router.get("/{agendamento_id}", response_model=AgendamentoSaida)
def obter(agendamento_id: int, db: Session = Depends(get_db), u: Usuario = Depends(exigir(P.AGENDA_LER))):
    ag = service.obter(db, agendamento_id)
    unidade_permitida(u, ag.unidade_id)
    return ag


@router.get("/{agendamento_id}/historico", response_model=list[EventoHistorico], summary="Linha do tempo (RF07)")
def historico(agendamento_id: int, db: Session = Depends(get_db), u: Usuario = Depends(exigir(P.AGENDA_LER))):
    unidade_permitida(u, service.obter(db, agendamento_id).unidade_id)
    return service.historico(db, agendamento_id)


@router.post("/{agendamento_id}/cancelar", response_model=AgendamentoSaida,
             summary="Cancela pela recepção e libera a vaga para encaixe")
def cancelar(agendamento_id: int, dados: CancelamentoEntrada, db: Session = Depends(get_db),
             u: Usuario = Depends(exigir(P.AGENDA_ESCREVER))):
    return service.cancelar(db, agendamento_id, dados.motivo, u)


@router.post("/{agendamento_id}/comparecimento", response_model=AgendamentoSaida,
             summary="Registra comparecimento ou falta")
def comparecimento(agendamento_id: int, dados: ComparecimentoEntrada, db: Session = Depends(get_db),
                   u: Usuario = Depends(exigir(P.AGENDA_ESCREVER))):
    return service.registrar_comparecimento(db, agendamento_id, dados, u)
