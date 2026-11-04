from app.core import eventos
from app.modules.confirmacao import service


@eventos.assinar(eventos.MENSAGEM_ENVIADA)
def _mensagem_enviada(db, mensagem):
    service.ao_enviar_mensagem(db, mensagem)
