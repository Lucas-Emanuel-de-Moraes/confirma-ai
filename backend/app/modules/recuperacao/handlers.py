"""Assinaturas de eventos internos do módulo de recuperação (registradas ao importar este arquivo)."""

from app.core import eventos
from app.modules.recuperacao import service


@eventos.assinar(eventos.VAGA_LIBERADA)
def _vaga_liberada(db, agendamento, origem):
    service.liberar_vaga(db, agendamento, origem)


@eventos.assinar(eventos.AGENDAMENTO_CRIADO)
def _agendamento_criado(db, agendamento, origem):
    service.ao_criar_agendamento(db, agendamento, origem)


@eventos.assinar(eventos.MENSAGEM_ENVIADA)
def _mensagem_enviada(db, mensagem):
    service.ao_enviar_mensagem(db, mensagem)


@eventos.assinar(eventos.MENSAGEM_NAO_ENTREGUE)
def _mensagem_nao_entregue(db, mensagem):
    service.ao_falhar_mensagem(db, mensagem)


@eventos.assinar(eventos.AUTORIZACAO_REVOGADA)
def _autorizacao_revogada(db, paciente_id, origem):
    service.ao_revogar_autorizacao(db, paciente_id, origem)
