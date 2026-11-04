from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.paginacao import Pagina, ParamsPaginacao, params_paginacao
from app.modules.acesso import permissoes as P
from app.modules.acesso.dependencias import exigir, unidade_permitida
from app.modules.acesso.models import Usuario
from app.modules.agenda.schemas import AgendamentoSaida
from app.modules.recuperacao import service
from app.modules.recuperacao.models import StatusOferta, StatusVaga
from app.modules.recuperacao.schemas import CancelarOferta, OfertaSaida, VagaSaida

router_vagas = APIRouter(prefix="/vagas", tags=["Vagas e ofertas"])
router_ofertas = APIRouter(prefix="/ofertas", tags=["Vagas e ofertas"])


@router_vagas.get("", response_model=Pagina[VagaSaida], summary="Painel de vagas liberadas")
def listar_vagas(status: StatusVaga | None = None, unidade_id: int | None = None, inicio: datetime | None = None,
                 fim: datetime | None = None, params: ParamsPaginacao = Depends(params_paginacao),
                 db: Session = Depends(get_db), u: Usuario = Depends(exigir(P.OFERTAS_LER))):
    return service.listar_vagas(db, params, status=status, unidade_id=unidade_permitida(u, unidade_id),
                                inicio=inicio, fim=fim)


@router_vagas.get("/{vaga_id}", response_model=VagaSaida)
def obter_vaga(vaga_id: int, db: Session = Depends(get_db), _: Usuario = Depends(exigir(P.OFERTAS_LER))):
    return service.obter_vaga(db, vaga_id)


@router_vagas.post("/{vaga_id}/ofertar", response_model=VagaSaida,
                   summary="Consulta a fila de novo e oferta ao próximo elegível")
def ofertar(vaga_id: int, db: Session = Depends(get_db), u: Usuario = Depends(exigir(P.OFERTAS_GERENCIAR))):
    return service.ofertar_manual(db, vaga_id, u)


@router_ofertas.get("", response_model=Pagina[OfertaSaida], summary="Acompanha as ofertas de encaixe")
def listar_ofertas(status: StatusOferta | None = None, unidade_id: int | None = None, paciente_id: int | None = None,
                   vaga_id: int | None = None, params: ParamsPaginacao = Depends(params_paginacao),
                   db: Session = Depends(get_db), u: Usuario = Depends(exigir(P.OFERTAS_LER))):
    return service.listar_ofertas(db, params, status=status, unidade_id=unidade_permitida(u, unidade_id),
                                  paciente_id=paciente_id, vaga_id=vaga_id)


@router_ofertas.post("/{oferta_id}/cancelar", response_model=OfertaSaida, summary="Cancela a reserva (manual)")
def cancelar(oferta_id: int, dados: CancelarOferta, db: Session = Depends(get_db),
             u: Usuario = Depends(exigir(P.OFERTAS_GERENCIAR))):
    return service.cancelar_oferta(db, oferta_id, dados.motivo, dados.reofertar, u)


@router_ofertas.post("/{oferta_id}/aceitar", response_model=AgendamentoSaida,
                     summary="Registra aceite informado por telefone (devolve 409 se a vaga já foi tomada)")
def aceitar(oferta_id: int, db: Session = Depends(get_db), u: Usuario = Depends(exigir(P.OFERTAS_GERENCIAR))):
    return service.aceitar_manual(db, oferta_id, u)


@router_ofertas.post("/{oferta_id}/recusar", response_model=OfertaSaida, summary="Registra recusa informada por telefone")
def recusar(oferta_id: int, db: Session = Depends(get_db), u: Usuario = Depends(exigir(P.OFERTAS_GERENCIAR))):
    return service.recusar_manual(db, oferta_id, u)
