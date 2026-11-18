"""Adaptador para a WhatsApp Business Platform (Cloud API).

Requer conta comercial verificada, número cadastrado e, para mensagens iniciadas pela
empresa fora da janela de 24 h, mensagens-modelo aprovadas (seção 11.4). Por isso o
desenvolvimento usa o simulador; este adaptador segue a mesma interface e deve ser validado
com as credenciais reais da unidade (variáveis WHATSAPP_*).

Os botões de resposta carregam o identificador único no payload ("<identificador>|<opção>"),
o que permite validar o vínculo da resposta (RF24, RNF19).
"""

import hashlib
import hmac
import json
import logging

import httpx

from app.core.config import settings
from app.modules.notificacao.gateway import GatewayMensageria, MensagemSaida, RespostaRecebida, ResultadoEnvio

log = logging.getLogger("confirma_ai.whatsapp")


class WhatsAppCloudGateway(GatewayMensageria):
    nome = "whatsapp"

    def __init__(self, cliente: httpx.Client | None = None):
        self.cliente = cliente or httpx.Client(timeout=10.0)

    @property
    def _url(self) -> str:
        return f"{settings.WHATSAPP_API_URL}/{settings.WHATSAPP_API_VERSAO}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"

    def _modelo(self, tipo: str) -> str:
        return {
            "LEMBRETE_CONFIRMACAO": settings.WHATSAPP_TEMPLATE_LEMBRETE,
            "OFERTA_ENCAIXE": settings.WHATSAPP_TEMPLATE_OFERTA,
        }.get(tipo, "")

    def _payload(self, m: MensagemSaida) -> dict:
        base = {"messaging_product": "whatsapp", "recipient_type": "individual", "to": m.destino}
        modelo = self._modelo(m.tipo)
        if modelo:
            componentes = []
            if m.parametros_modelo:
                componentes.append({"type": "body",
                                    "parameters": [{"type": "text", "text": p} for p in m.parametros_modelo]})
            for i, (codigo, _) in enumerate(m.opcoes):
                componentes.append({"type": "button", "sub_type": "quick_reply", "index": str(i),
                                    "parameters": [{"type": "payload", "payload": f"{m.identificador}|{codigo}"}]})
            return {**base, "type": "template",
                    "template": {"name": modelo, "language": {"code": settings.WHATSAPP_TEMPLATE_IDIOMA},
                                 "components": componentes}}
        if m.opcoes and m.identificador:
            botoes = [{"type": "reply", "reply": {"id": f"{m.identificador}|{codigo}", "title": rotulo[:20]}}
                      for codigo, rotulo in m.opcoes[:3]]
            return {**base, "type": "interactive",
                    "interactive": {"type": "button", "body": {"text": m.texto[:1024]}, "action": {"buttons": botoes}}}
        return {**base, "type": "text", "text": {"body": m.texto}}

    def enviar(self, mensagem: MensagemSaida) -> ResultadoEnvio:
        try:
            resp = self.cliente.post(
                self._url,
                headers={"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"},
                json=self._payload(mensagem),
            )
        except httpx.HTTPError as exc:
            return ResultadoEnvio(False, erro=f"Erro de rede: {exc.__class__.__name__}", temporario=True)
        if resp.status_code < 300:
            dados = resp.json()
            return ResultadoEnvio(True, id_externo=(dados.get("messages") or [{}])[0].get("id"))
        temporario = resp.status_code == 429 or resp.status_code >= 500
        return ResultadoEnvio(False, erro=f"HTTP {resp.status_code}: {resp.text[:200]}", temporario=temporario)

    def verificar_assinatura(self, corpo: bytes, headers: dict[str, str]) -> bool:
        recebida = headers.get("x-hub-signature-256", "")
        esperada = "sha256=" + hmac.new(settings.WHATSAPP_APP_SECRET.encode(), corpo, hashlib.sha256).hexdigest()
        return bool(settings.WHATSAPP_APP_SECRET) and hmac.compare_digest(recebida, esperada)

    def interpretar_webhook(self, corpo: bytes) -> list[RespostaRecebida]:
        dados = json.loads(corpo or b"{}")
        respostas: list[RespostaRecebida] = []
        for entrada in dados.get("entry", []):
            for mudanca in entrada.get("changes", []):
                for msg in mudanca.get("value", {}).get("messages", []):
                    telefone = msg.get("from", "")
                    contexto = (msg.get("context") or {}).get("id")
                    tipo = msg.get("type")
                    payload = None
                    if tipo == "interactive":
                        payload = (msg.get("interactive", {}).get("button_reply") or {}).get("id")
                    elif tipo == "button":
                        payload = msg.get("button", {}).get("payload")
                    if payload and "|" in payload:
                        identificador, opcao = payload.split("|", 1)
                        respostas.append(RespostaRecebida(telefone, opcao, identificador, contexto))
                    elif tipo == "text":
                        respostas.append(RespostaRecebida(telefone, msg.get("text", {}).get("body", ""), None, contexto))
        return respostas
