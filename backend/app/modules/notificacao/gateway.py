"""Interface única do adaptador de mensageria (PB13, RNF13).

Os demais módulos só conhecem esta interface. A implementação é escolhida pela variável
MENSAGERIA_PROVEDOR: "simulador" (desenvolvimento e testes) ou "whatsapp" (Cloud API).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.core.config import settings


@dataclass
class MensagemSaida:
    destino: str
    texto: str
    tipo: str
    chave_idempotencia: str
    identificador: str | None = None
    opcoes: list[tuple[str, str]] = field(default_factory=list)  # (código, rótulo do botão)
    parametros_modelo: list[str] = field(default_factory=list)  # variáveis da mensagem-modelo do WhatsApp


@dataclass
class ResultadoEnvio:
    sucesso: bool
    id_externo: str | None = None
    erro: str | None = None
    temporario: bool = True  # falha temporária gera retentativa; definitiva encerra o envio


@dataclass
class RespostaRecebida:
    telefone: str
    texto: str
    identificador: str | None = None
    id_contexto: str | None = None  # id externo da mensagem que o paciente respondeu


class GatewayMensageria(ABC):
    nome: str = "base"

    @abstractmethod
    def enviar(self, mensagem: MensagemSaida) -> ResultadoEnvio: ...

    @abstractmethod
    def verificar_assinatura(self, corpo: bytes, headers: dict[str, str]) -> bool: ...

    @abstractmethod
    def interpretar_webhook(self, corpo: bytes) -> list[RespostaRecebida]: ...


_gateway: GatewayMensageria | None = None


def obter_gateway() -> GatewayMensageria:
    global _gateway
    if _gateway is None:
        if settings.MENSAGERIA_PROVEDOR == "whatsapp":
            from app.modules.notificacao.whatsapp import WhatsAppCloudGateway

            _gateway = WhatsAppCloudGateway()
        else:
            from app.modules.notificacao.simulador import SimuladorGateway

            _gateway = SimuladorGateway()
    return _gateway


def definir_gateway(gateway: GatewayMensageria | None) -> None:
    """Permite trocar o provedor nos testes."""
    global _gateway
    _gateway = gateway
