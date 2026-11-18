from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.erros import RegraNegocio
from app.core.relogio import hoje
from app.modules.acesso import permissoes as P
from app.modules.acesso.dependencias import exigir, unidade_permitida
from app.modules.acesso.models import Usuario
from app.modules.indicadores import service

router = APIRouter(prefix="/indicadores", tags=["Indicadores"])


@router.get("", summary="Indicadores de absenteísmo e recuperação de vagas (RF19)")
def indicadores(
    inicio: date | None = Query(None, description="Padrão: 30 dias atrás"),
    fim: date | None = Query(None, description="Padrão: 30 dias à frente"),
    unidade_id: int | None = None,
    especialidade_id: int | None = None,
    profissional_id: int | None = None,
    db: Session = Depends(get_db),
    u: Usuario = Depends(exigir(P.INDICADORES_LER)),
):
    inicio = inicio or hoje() - timedelta(days=30)
    fim = fim or hoje() + timedelta(days=30)
    if inicio > fim:
        raise RegraNegocio("inicio deve ser anterior ou igual a fim.")
    return service.calcular(db, inicio, fim, unidade_permitida(u, unidade_id), especialidade_id, profissional_id)
