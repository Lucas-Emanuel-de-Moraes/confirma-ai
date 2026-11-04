from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.acesso import permissoes as P
from app.modules.acesso.dependencias import exigir
from app.modules.acesso.models import Usuario
from app.modules.parametros import service
from app.modules.parametros.schemas import ParametrosEntrada, ParametrosSaida

router = APIRouter(prefix="/unidades", tags=["Parâmetros operacionais"])


@router.get("/{unidade_id}/parametros", response_model=ParametrosSaida, summary="Parâmetros vigentes da unidade")
def obter(unidade_id: int, db: Session = Depends(get_db), _: Usuario = Depends(exigir(P.PARAMETROS_LER))):
    return service.obter(db, unidade_id)


@router.put("/{unidade_id}/parametros", response_model=ParametrosSaida, summary="Cria nova versão dos parâmetros")
def atualizar(
    unidade_id: int, dados: ParametrosEntrada, db: Session = Depends(get_db),
    usuario: Usuario = Depends(exigir(P.PARAMETROS_ESCREVER)),
):
    return service.atualizar(db, unidade_id, dados, usuario)


@router.get("/{unidade_id}/parametros/historico", response_model=list[ParametrosSaida])
def historico(unidade_id: int, db: Session = Depends(get_db), _: Usuario = Depends(exigir(P.PARAMETROS_LER))):
    return service.historico(db, unidade_id)
