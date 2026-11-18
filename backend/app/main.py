"""Cria o app FastAPI e registra os routers dos módulos (seção 11.9)."""

import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text

import app.models  # noqa: F401  – registra todas as tabelas
import app.modules.confirmacao.handlers  # noqa: F401  – assinaturas de eventos internos
import app.modules.recuperacao.handlers  # noqa: F401
from app import tarefas
from app.core import database
from app.core.config import settings
from app.core.erros import registrar_handlers
from app.modules.acesso.router import router_auth, router_usuarios
from app.modules.agenda.router import router as router_agenda
from app.modules.auditoria.router import router as router_auditoria
from app.modules.cadastros.router import router_estrutura, router_pacientes
from app.modules.confirmacao.router import router as router_webhook
from app.modules.fila.router import router_fila, router_remarcacoes
from app.modules.indicadores.router import router as router_indicadores
from app.modules.lgpd.router import router_consentimento, router_retencao, router_titular
from app.modules.notificacao.router import router as router_simulador
from app.modules.parametros.router import router as router_parametros
from app.modules.recuperacao.router import router_ofertas, router_vagas

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.AGENDADOR_ATIVO:
        tarefas.iniciar()
    yield
    tarefas.parar()


app = FastAPI(
    title="Confirma Aí – API",
    version=settings.APP_VERSAO,
    description=(
        "Back-end do sistema de confirmação de consultas e recuperação de vagas perdidas.\n\n"
        "**Como testar:** use `POST /api/v1/auth/login` (botão *Authorize*, usuário `admin`) "
        "e siga o roteiro do README."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.FRONTEND_URL.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
registrar_handlers(app)
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

api = APIRouter(prefix="/api/v1")
for r in (
    router_auth, router_usuarios, router_pacientes, router_consentimento, router_estrutura, router_parametros,
    router_agenda, router_remarcacoes, router_fila, router_vagas, router_ofertas, router_indicadores,
    router_titular, router_retencao, router_auditoria, router_webhook, tarefas.router,
):
    api.include_router(r)
if settings.MENSAGERIA_PROVEDOR == "simulador":
    api.include_router(router_simulador)
app.include_router(api)


@app.get("/api/health", tags=["Saúde"], summary="Situação da aplicação")
def health():
    try:
        with database.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        banco = "ok"
    except Exception:  # noqa: BLE001
        banco = "indisponivel"
    corpo = {
        "status": "ok" if banco == "ok" else "degradado",
        "aplicacao": settings.APP_NOME,
        "versao": settings.APP_VERSAO,
        "banco": banco,
        "mensageria": settings.MENSAGERIA_PROVEDOR,
        "agendador": bool(tarefas.agendador and tarefas.agendador.running),
    }
    return JSONResponse(corpo, status_code=200 if banco == "ok" else 503)
