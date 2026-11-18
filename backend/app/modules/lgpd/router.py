from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.paginacao import Pagina, ParamsPaginacao, params_paginacao
from app.modules.acesso import permissoes as P
from app.modules.acesso.dependencias import exigir
from app.modules.acesso.models import Usuario
from app.modules.auditoria import service as auditoria
from app.modules.cadastros.schemas import PacienteSaida
from app.modules.lgpd import service
from app.modules.lgpd.models import StatusRequisicao
from app.modules.lgpd.schemas import (
    AutorizacaoEntrada,
    ConsentimentoSaida,
    PoliticaAtualizar,
    PoliticaSaida,
    PreferenciasContato,
    RequisicaoCriar,
    RequisicaoResolver,
    RequisicaoResolvida,
    RequisicaoSaida,
)

router_consentimento = APIRouter(prefix="/pacientes", tags=["LGPD – autorização de contato"])
router_titular = APIRouter(prefix="/requisicoes-titular", tags=["LGPD – direitos do titular"])
router_retencao = APIRouter(prefix="/retencao", tags=["LGPD – retenção de dados"])


@router_consentimento.post("/{paciente_id}/autorizacao", response_model=PacienteSaida,
                           summary="Registra a autorização de contato por mensageria (RF21)")
def autorizar(paciente_id: int, dados: AutorizacaoEntrada, db: Session = Depends(get_db),
              u: Usuario = Depends(exigir(P.PACIENTES_ESCREVER))):
    return service.autorizar(db, paciente_id, dados, u)


@router_consentimento.delete("/{paciente_id}/autorizacao", response_model=PacienteSaida,
                             summary="Revoga a autorização (efeito imediato – RN16)")
def revogar(paciente_id: int, motivo: str | None = Query(None, max_length=200), db: Session = Depends(get_db),
            u: Usuario = Depends(exigir(P.PACIENTES_ESCREVER))):
    return service.revogar(db, paciente_id, motivo, u)


@router_consentimento.put("/{paciente_id}/preferencias-contato", response_model=PacienteSaida)
def preferencias(paciente_id: int, dados: PreferenciasContato, db: Session = Depends(get_db),
                 u: Usuario = Depends(exigir(P.PACIENTES_ESCREVER))):
    return service.atualizar_preferencias(db, paciente_id, dados.preferencias, u)


@router_consentimento.get("/{paciente_id}/consentimento", response_model=ConsentimentoSaida,
                          summary="Situação e histórico da autorização")
def consentimento(paciente_id: int, db: Session = Depends(get_db), _: Usuario = Depends(exigir(P.PACIENTES_LER))):
    return service.consultar_consentimento(db, paciente_id)


@router_titular.get("", response_model=Pagina[RequisicaoSaida])
def listar(status: StatusRequisicao | None = None, paciente_id: int | None = None,
           params: ParamsPaginacao = Depends(params_paginacao), db: Session = Depends(get_db),
           _: Usuario = Depends(exigir(P.TITULAR_GERENCIAR))):
    return service.listar_requisicoes(db, params, status, paciente_id)


@router_titular.post("", response_model=RequisicaoSaida, status_code=201, summary="Registra requisição do titular")
def criar(dados: RequisicaoCriar, db: Session = Depends(get_db), u: Usuario = Depends(exigir(P.TITULAR_GERENCIAR))):
    return service.criar_requisicao(db, dados, u)


@router_titular.patch("/{req_id}", response_model=RequisicaoResolvida, summary="Atende a requisição (UC11)")
def resolver(req_id: int, dados: RequisicaoResolver, db: Session = Depends(get_db),
             u: Usuario = Depends(exigir(P.TITULAR_GERENCIAR))):
    return service.resolver_requisicao(db, req_id, dados, u)


@router_retencao.get("/politicas", response_model=list[PoliticaSaida])
def listar_politicas(db: Session = Depends(get_db), _: Usuario = Depends(exigir(P.RETENCAO_GERENCIAR))):
    resultado = service.politicas(db)
    db.commit()
    return resultado


@router_retencao.put("/politicas", response_model=list[PoliticaSaida], summary="Define prazos por categoria (RF23)")
def atualizar_politicas(dados: list[PoliticaAtualizar], db: Session = Depends(get_db),
                        u: Usuario = Depends(exigir(P.RETENCAO_GERENCIAR))):
    return service.atualizar_politicas(db, dados, u)


@router_retencao.post("/executar", summary="Executa agora a rotina de eliminação/anonimização")
def executar(db: Session = Depends(get_db), u: Usuario = Depends(exigir(P.RETENCAO_GERENCIAR))):
    return service.executar_retencao(db, auditoria.origem_usuario(u))
