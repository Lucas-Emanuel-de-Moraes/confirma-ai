from fastapi import APIRouter, Depends, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.erros import Proibido
from app.modules.confirmacao import service

router = APIRouter(prefix="/webhooks", tags=["Webhook de mensageria"])


@router.post("/mensageria", summary="Recebe respostas do provedor (assinatura verificada)")
async def webhook(request: Request, db: Session = Depends(get_db)):
    """Simulador: JSON `{telefone, identificador, resposta}` com cabeçalho `X-Assinatura`
    (HMAC-SHA256 do corpo com WEBHOOK_SEGREDO). WhatsApp: payload da Cloud API com `X-Hub-Signature-256`."""
    corpo = await request.body()
    return await run_in_threadpool(service.receber_webhook, db, corpo, dict(request.headers))


@router.get("/mensageria", response_class=PlainTextResponse, summary="Verificação do webhook pelo WhatsApp")
def verificar(
    modo: str = Query("", alias="hub.mode"),
    token: str = Query("", alias="hub.verify_token"),
    desafio: str = Query("", alias="hub.challenge"),
):
    if modo == "subscribe" and settings.WHATSAPP_VERIFY_TOKEN and token == settings.WHATSAPP_VERIFY_TOKEN:
        return desafio
    raise Proibido("Token de verificação inválido.")
