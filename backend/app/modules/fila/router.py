from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.paginacao import Pagina, ParamsPaginacao, params_paginacao
from app.modules.acesso import permissoes as P
from app.modules.acesso.dependencias import exigir
from app.modules.acesso.models import Usuario
from app.modules.fila import service
from app.modules.fila.models import StatusRemarcacao
from app.modules.fila.schemas import (
    FilaCriar,
    FilaSaida,
    PreferenciasAtualizar,
    RemarcacaoPendente,
    RemarcacaoResolver,
    RemarcacaoSaida,
)

router_fila = APIRouter(prefix="/fila-espera", tags=["Fila de espera"])
router_remarcacoes = APIRouter(prefix="/remarcacoes", tags=["Remarcações"])


@router_fila.get("", response_model=Pagina[FilaSaida])
def listar(
    especialidade_id: int | None = None, unidade_id: int | None = None, ativo: bool | None = True,
    disponivel: bool | None = None, paciente_id: int | None = None, busca: str | None = None,
    params: ParamsPaginacao = Depends(params_paginacao), db: Session = Depends(get_db),
    _: Usuario = Depends(exigir(P.FILA_LER)),
):
    return service.listar(db, params, especialidade_id=especialidade_id, unidade_id=unidade_id, ativo=ativo,
                          disponivel=disponivel, paciente_id=paciente_id, busca=busca)


@router_fila.post("", response_model=FilaSaida, status_code=201, summary="Coloca paciente na fila (RF09)")
def adicionar(dados: FilaCriar, db: Session = Depends(get_db), u: Usuario = Depends(exigir(P.FILA_ESCREVER))):
    return service.adicionar(db, dados, u)


@router_fila.get("/{fila_id}", response_model=FilaSaida)
def obter(fila_id: int, db: Session = Depends(get_db), _: Usuario = Depends(exigir(P.FILA_LER))):
    return service.obter(db, fila_id)


@router_fila.put("/{fila_id}/preferencias", response_model=FilaSaida,
                 summary="Disponibilidade para encaixe: locais e períodos (RF10, HU03)")
def preferencias(fila_id: int, dados: PreferenciasAtualizar, db: Session = Depends(get_db),
                 u: Usuario = Depends(exigir(P.FILA_ESCREVER))):
    return service.atualizar_preferencias(db, fila_id, dados, u)


@router_fila.patch("/{fila_id}/remover", response_model=FilaSaida, summary="Retira o paciente da fila")
def remover(fila_id: int, motivo: str = Query("REMOVIDO_PELA_RECEPCAO", max_length=80),
            db: Session = Depends(get_db), u: Usuario = Depends(exigir(P.FILA_ESCREVER))):
    return service.remover(db, fila_id, motivo, u)


@router_remarcacoes.get("", response_model=Pagina[RemarcacaoPendente], summary="Painel de pendências de remarcação")
def listar_remarcacoes(status: StatusRemarcacao | None = StatusRemarcacao.PENDENTE,
                       params: ParamsPaginacao = Depends(params_paginacao), db: Session = Depends(get_db),
                       _: Usuario = Depends(exigir(P.AGENDA_LER))):
    return service.listar_remarcacoes(db, params, status)


@router_remarcacoes.patch("/{solicitacao_id}", response_model=RemarcacaoSaida, summary="Trata a remarcação")
def resolver(solicitacao_id: int, dados: RemarcacaoResolver, db: Session = Depends(get_db),
             u: Usuario = Depends(exigir(P.AGENDA_ESCREVER))):
    return service.resolver_remarcacao(db, solicitacao_id, dados, u)
