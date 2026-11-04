"""Eventos internos entre módulos (ex.: VagaLiberada).

Os módulos não se chamam diretamente quando isso criaria dependência circular: o módulo de
agenda publica "VagaLiberada" e o módulo de recuperação reage. Os assinantes rodam de forma
síncrona, dentro da mesma transação de quem publicou, o que preserva a consistência da agenda.
Se o volume crescer (RNF15), estes eventos podem ser movidos para uma fila externa.
"""

from collections import defaultdict
from collections.abc import Callable

VAGA_LIBERADA = "VagaLiberada"
AGENDAMENTO_CRIADO = "AgendamentoCriado"
MENSAGEM_ENVIADA = "MensagemEnviada"
MENSAGEM_NAO_ENTREGUE = "MensagemNaoEntregue"
AUTORIZACAO_REVOGADA = "AutorizacaoRevogada"

_assinantes: dict[str, list[Callable]] = defaultdict(list)


def assinar(evento: str):
    def decorador(funcao: Callable) -> Callable:
        if funcao not in _assinantes[evento]:
            _assinantes[evento].append(funcao)
        return funcao

    return decorador


def publicar(evento: str, **dados) -> None:
    for funcao in list(_assinantes[evento]):
        funcao(**dados)
