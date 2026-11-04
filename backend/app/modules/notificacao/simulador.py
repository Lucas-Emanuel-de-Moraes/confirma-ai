"""Simulador local do provedor de mensageria, com a mesma interface do WhatsApp.

- As mensagens "enviadas" ficam numa caixa de saída em memória e aparecem no log.
- Telefones terminados em SIMULADOR_SUFIXO_FALHA (padrão 9999) simulam falha temporária,
  para testar retentativas e falha definitiva (RNF12).
- O webhook do simulador recebe JSON {"telefone", "identificador", "resposta"} assinado com
  HMAC-SHA256 (cabeçalho X-Assinatura) usando WEBHOOK_SEGREDO.
"""

import hashlib
import hmac
import json
import logging
import threading
import uuid
from collections import deque

from app.core.config import settings
from app.core.relogio import agora
from app.modules.notificacao.gateway import GatewayMensageria, MensagemSaida, RespostaRecebida, ResultadoEnvio

log = logging.getLogger("confirma_ai.simulador")


def assinar(corpo: bytes) -> str:
    return hmac.new(settings.WEBHOOK_SEGREDO.encode(), corpo, hashlib.sha256).hexdigest()


class SimuladorGateway(GatewayMensageria):
    nome = "simulador"

    def __init__(self):
        self.caixa_saida: deque[dict] = deque(maxlen=500)
        self._enviadas_por_chave: dict[str, str] = {}
        self._lock = threading.Lock()

    def enviar(self, mensagem: MensagemSaida) -> ResultadoEnvio:
        with self._lock:
            # Idempotência do lado do provedor: mesma chave devolve o mesmo envio
            if mensagem.chave_idempotencia in self._enviadas_por_chave:
                return ResultadoEnvio(True, self._enviadas_por_chave[mensagem.chave_idempotencia])
            if settings.SIMULADOR_SUFIXO_FALHA and mensagem.destino.endswith(settings.SIMULADOR_SUFIXO_FALHA):
                return ResultadoEnvio(False, erro="Falha simulada do provedor", temporario=True)
            id_externo = f"sim-{uuid.uuid4().hex[:12]}"
            self._enviadas_por_chave[mensagem.chave_idempotencia] = id_externo
            self.caixa_saida.append({
                "id_externo": id_externo,
                "data_hora": agora().isoformat(),
                "destino": mensagem.destino,
                "tipo": mensagem.tipo,
                "texto": mensagem.texto,
                "identificador": mensagem.identificador,
                "opcoes": [codigo for codigo, _ in mensagem.opcoes],
            })
        log.info("[SIMULADOR] Para %s (%s): %s", mensagem.destino[-4:], mensagem.tipo, mensagem.texto)
        return ResultadoEnvio(True, id_externo)

    def verificar_assinatura(self, corpo: bytes, headers: dict[str, str]) -> bool:
        recebida = headers.get("x-assinatura", "")
        return hmac.compare_digest(recebida, assinar(corpo))

    def interpretar_webhook(self, corpo: bytes) -> list[RespostaRecebida]:
        dados = json.loads(corpo or b"{}")
        itens = dados if isinstance(dados, list) else [dados]
        return [
            RespostaRecebida(
                telefone=str(i.get("telefone", "")),
                texto=str(i.get("resposta", "")),
                identificador=i.get("identificador"),
            )
            for i in itens
        ]

    def limpar(self) -> None:
        with self._lock:
            self.caixa_saida.clear()
            self._enviadas_por_chave.clear()
