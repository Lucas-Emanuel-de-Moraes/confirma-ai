"""Erros de domínio e formato padronizado de resposta de erro: { codigo, mensagem, campos }."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("confirma_ai.erros")


class ErroApp(Exception):
    status_code = 400
    codigo_padrao = "ERRO"

    def __init__(self, mensagem: str, codigo: str | None = None, campos: list | None = None):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.codigo = codigo or self.codigo_padrao
        self.campos = campos or []


class NaoEncontrado(ErroApp):
    status_code = 404
    codigo_padrao = "NAO_ENCONTRADO"


class Conflito(ErroApp):
    """HTTP 409: registro duplicado ou conflito de concorrência (RF17, RNF03)."""

    status_code = 409
    codigo_padrao = "CONFLITO"


class RegraNegocio(ErroApp):
    status_code = 422
    codigo_padrao = "REGRA_NEGOCIO"


class NaoAutorizado(ErroApp):
    status_code = 401
    codigo_padrao = "NAO_AUTENTICADO"


class Proibido(ErroApp):
    status_code = 403
    codigo_padrao = "SEM_PERMISSAO"


def _corpo(codigo: str, mensagem: str, campos: list | None = None) -> dict:
    return {"codigo": codigo, "mensagem": mensagem, "campos": campos or []}


def registrar_handlers(app: FastAPI) -> None:
    @app.exception_handler(ErroApp)
    async def _erro_app(_: Request, exc: ErroApp):
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return JSONResponse(_corpo(exc.codigo, exc.mensagem, exc.campos), exc.status_code, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def _validacao(_: Request, exc: RequestValidationError):
        campos = [
            {"campo": ".".join(str(p) for p in e["loc"] if p != "body"), "erro": e["msg"]}
            for e in exc.errors()
        ]
        return JSONResponse(_corpo("VALIDACAO", "Dados de entrada inválidos.", campos), 422)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        mensagem = exc.detail if isinstance(exc.detail, str) else "Erro na requisição."
        return JSONResponse(
            _corpo(f"HTTP_{exc.status_code}", mensagem), exc.status_code, headers=getattr(exc, "headers", None)
        )

    @app.exception_handler(IntegrityError)
    async def _integridade(_: Request, exc: IntegrityError):
        log.info("Violação de integridade: %s", exc.orig)
        return JSONResponse(
            _corpo("CONFLITO", "A operação conflita com um registro existente (duplicidade ou vaga ocupada)."),
            409,
        )

    @app.exception_handler(StaleDataError)
    async def _concorrencia(_: Request, exc: StaleDataError):
        return JSONResponse(
            _corpo("CONFLITO_CONCORRENCIA", "O registro foi alterado por outra operação. Tente novamente."),
            409,
        )
