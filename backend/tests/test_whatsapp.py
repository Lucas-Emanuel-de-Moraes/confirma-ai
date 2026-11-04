"""Adaptador da WhatsApp Cloud API: formato do envio, assinatura e leitura do webhook (sem rede)."""

import hashlib
import hmac
import json

import httpx

from app.core.config import settings
from app.modules.notificacao.gateway import MensagemSaida
from app.modules.notificacao.whatsapp import WhatsAppCloudGateway


def _gateway(resposta: httpx.Response, capturado: list):
    def handler(request: httpx.Request):
        capturado.append(json.loads(request.content))
        return resposta

    return WhatsAppCloudGateway(httpx.Client(transport=httpx.MockTransport(handler)))


def _msg():
    return MensagemSaida(destino="5565999990001", texto="Confirma?", tipo="LEMBRETE_CONFIRMACAO",
                         chave_idempotencia="k", identificador="abc123", opcoes=[("SIM", "Sim"), ("NAO", "Não")])


def test_envio_com_botoes_carrega_identificador():
    enviados = []
    gw = _gateway(httpx.Response(200, json={"messages": [{"id": "wamid.X"}]}), enviados)
    r = gw.enviar(_msg())
    assert r.sucesso and r.id_externo == "wamid.X"
    botoes = enviados[0]["interactive"]["action"]["buttons"]
    assert [b["reply"]["id"] for b in botoes] == ["abc123|SIM", "abc123|NAO"]


def test_erros_temporarios_e_definitivos():
    assert _gateway(httpx.Response(503), []).enviar(_msg()).temporario is True
    assert _gateway(httpx.Response(429), []).enviar(_msg()).temporario is True
    assert _gateway(httpx.Response(400, text="bad"), []).enviar(_msg()).temporario is False


def test_assinatura_e_leitura_do_webhook(monkeypatch):
    monkeypatch.setattr(settings, "WHATSAPP_APP_SECRET", "segredo")
    corpo = json.dumps({"entry": [{"changes": [{"value": {"messages": [
        {"from": "5565999990001", "type": "interactive", "context": {"id": "wamid.X"},
         "interactive": {"type": "button_reply", "button_reply": {"id": "abc123|SIM", "title": "Sim"}}},
        {"from": "5565999990002", "type": "text", "text": {"body": "nao"}, "context": {"id": "wamid.Y"}},
    ]}}]}]}).encode()
    gw = WhatsAppCloudGateway(httpx.Client())
    assinatura = "sha256=" + hmac.new(b"segredo", corpo, hashlib.sha256).hexdigest()
    assert gw.verificar_assinatura(corpo, {"x-hub-signature-256": assinatura})
    assert not gw.verificar_assinatura(corpo, {"x-hub-signature-256": "sha256=errada"})
    r1, r2 = gw.interpretar_webhook(corpo)
    assert (r1.identificador, r1.texto, r1.id_contexto) == ("abc123", "SIM", "wamid.X")
    assert (r2.identificador, r2.texto, r2.id_contexto) == (None, "nao", "wamid.Y")
