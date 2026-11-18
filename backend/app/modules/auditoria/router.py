from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.paginacao import Pagina, ParamsPaginacao, params_paginacao
from app.modules.acesso import permissoes as P
from app.modules.acesso.dependencias import exigir
from app.modules.acesso.models import Usuario
from app.modules.auditoria import service

router = APIRouter(prefix="/auditoria", tags=["Auditoria"])


class LogSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    acao: str
    entidade: str
    entidade_id: str | None
    data_hora: datetime
    origem: str
    usuario_id: int | None
    detalhes: dict | None


@router.get("", response_model=Pagina[LogSaida], summary="Consulta de logs (somente administrador)")
def listar(
    entidade: str | None = None,
    entidade_id: str | None = None,
    acao: str | None = None,
    inicio: datetime | None = None,
    fim: datetime | None = None,
    params: ParamsPaginacao = Depends(params_paginacao),
    db: Session = Depends(get_db),
    _: Usuario = Depends(exigir(P.AUDITORIA_LER)),
):
    return service.listar(db, params, entidade, entidade_id, acao, inicio, fim)
