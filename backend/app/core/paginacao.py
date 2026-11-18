"""Listas paginadas (page, size) conforme a convenção da API (seção 11.5)."""

from dataclasses import dataclass
from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

T = TypeVar("T")


class Pagina(BaseModel, Generic[T]):
    itens: list[T]
    total: int
    page: int
    size: int


@dataclass
class ParamsPaginacao:
    page: int = 1
    size: int = 20


def params_paginacao(
    page: int = Query(1, ge=1, description="Número da página (inicia em 1)"),
    size: int = Query(20, ge=1, le=100, description="Itens por página (máx. 100)"),
) -> ParamsPaginacao:
    return ParamsPaginacao(page=page, size=size)


def paginar(db: Session, stmt: Select, params: ParamsPaginacao) -> dict:
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    itens = db.scalars(stmt.offset((params.page - 1) * params.size).limit(params.size)).unique().all()
    return {"itens": itens, "total": total, "page": params.page, "size": params.size}
