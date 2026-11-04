"""Registro, visualização e ciclo de vida dos agendamentos (RF03, RF04, RF07, RN01, RN02, RN14, UC02)."""

import secrets
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import eventos
from app.core.erros import Conflito, NaoEncontrado, RegraNegocio
from app.core.paginacao import ParamsPaginacao, paginar
from app.core.relogio import agora
from app.modules.agenda import repository as repo
from app.modules.agenda.models import (
    STATUS_LIBERAM_VAGA,
    Agendamento,
    HistoricoComparecimento,
    HistoricoStatusAgendamento,
    StatusAgendamento,
    TipoComparecimento,
)
from app.modules.agenda.schemas import AgendamentoCriar, ComparecimentoEntrada, EventoHistorico
from app.modules.auditoria import service as auditoria
from app.modules.cadastros import repository as cad_repo
from app.modules.cadastros.models import Especialidade, Paciente, Profissional, UnidadeSaude

S = StatusAgendamento

# Máquina de estados do agendamento (Figura 3 da seção 11.7)
TRANSICOES: dict[StatusAgendamento, set[StatusAgendamento]] = {
    S.AGENDADO: {S.AGUARDANDO_RESPOSTA, S.CONFIRMADO, S.NAO_CONFIRMADO, S.CANCELADO, S.REMARCACAO_SOLICITADA,
                 S.REALIZADO, S.FALTA},
    S.AGUARDANDO_RESPOSTA: {S.CONFIRMADO, S.NAO_CONFIRMADO, S.CANCELADO, S.REMARCACAO_SOLICITADA, S.SEM_RESPOSTA,
                            S.REALIZADO, S.FALTA},
    S.CONFIRMADO: {S.CANCELADO, S.REMARCACAO_SOLICITADA, S.REALIZADO, S.FALTA},
    S.REMARCACAO_SOLICITADA: {S.CONFIRMADO, S.CANCELADO, S.REALIZADO, S.FALTA},
    S.NAO_CONFIRMADO: set(),
    S.CANCELADO: set(),
    S.SEM_RESPOSTA: set(),
    S.REALIZADO: set(),
    S.FALTA: set(),
}


def obter(db: Session, agendamento_id: int, para_atualizar: bool = False) -> Agendamento:
    if para_atualizar:
        ag = db.scalar(
            select(Agendamento)
            .where(Agendamento.id == agendamento_id)
            .with_for_update(of=Agendamento)
            .execution_options(populate_existing=True)
        )
    else:
        ag = db.get(Agendamento, agendamento_id)
    if ag is None:
        raise NaoEncontrado("Agendamento não encontrado.")
    return ag


def _gerar_numero() -> str:
    return f"AG{agora():%Y%m%d}-{secrets.token_hex(3).upper()}"


def validar_disponibilidade(
    db: Session,
    unidade_id: int,
    profissional_id: int,
    especialidade_id: int,
    data_hora: datetime,
    validar_horario: bool = True,
    ignorar_reserva: bool = False,
) -> None:
    """Valida RN01, RN02 e RN14 antes de ocupar um horário. Lança erro com o motivo."""
    unidade = db.get(UnidadeSaude, unidade_id)
    prof = db.get(Profissional, profissional_id)
    esp = db.get(Especialidade, especialidade_id)
    campos = []
    if unidade is None or not unidade.ativo:
        campos.append({"campo": "unidade_id", "erro": "inexistente ou inativa"})
    if prof is None or not prof.ativo:
        campos.append({"campo": "profissional_id", "erro": "inexistente ou inativo"})
    if esp is None or not esp.ativo:
        campos.append({"campo": "especialidade_id", "erro": "inexistente ou inativa"})
    if campos:
        raise RegraNegocio("Dados do agendamento inválidos.", campos=campos)
    if not prof.possui_especialidade(esp.id):
        raise RegraNegocio("O profissional não atende esta especialidade.",
                           campos=[{"campo": "especialidade_id", "erro": "não atendida pelo profissional"}])
    if not prof.atende_na_unidade(unidade.id):
        raise RegraNegocio("O profissional não atende nesta unidade.",
                           campos=[{"campo": "unidade_id", "erro": "profissional não vinculado"}])
    if unidade.especialidades and not any(e.id == esp.id for e in unidade.especialidades):
        raise RegraNegocio("A unidade não oferece esta especialidade.",
                           campos=[{"campo": "especialidade_id", "erro": "não oferecida pela unidade"}])
    if data_hora <= agora():
        raise RegraNegocio("A data e hora do agendamento devem estar no futuro.",
                           campos=[{"campo": "data_hora", "erro": "no passado"}])
    if validar_horario and cad_repo.horario_que_atende(db, prof.id, unidade.id, data_hora) is None:
        raise RegraNegocio("O profissional não tem horário de atendimento nesta unidade neste dia e hora.",
                           codigo="FORA_DO_HORARIO", campos=[{"campo": "data_hora", "erro": "fora do horário"}])
    bloqueio = cad_repo.bloqueio_vigente(db, unidade.id, prof.id, data_hora)
    if bloqueio is not None:
        raise RegraNegocio(f"Agenda bloqueada neste horário ({bloqueio.tipo.value}: {bloqueio.motivo or '-'}).",
                           codigo="AGENDA_BLOQUEADA")
    if repo.ocupante_do_horario(db, prof.id, data_hora) is not None:
        raise Conflito(
            "Horário já ocupado para este profissional. Cadastre o paciente na fila de espera "
            "(POST /api/v1/fila-espera) para receber uma oferta de encaixe.",
            codigo="HORARIO_OCUPADO",
        )
    if not ignorar_reserva and repo.vaga_em_oferta(db, prof.id, data_hora) is not None:
        raise Conflito("Este horário está reservado temporariamente para uma oferta de encaixe (RN02).",
                       codigo="VAGA_RESERVADA")


def criar(
    db: Session,
    dados: AgendamentoCriar,
    origem: str,
    usuario_id: int | None = None,
    origem_tipo: str = "recepcao",
    validar_horario: bool = True,
    ignorar_reserva: bool = False,
    commit: bool = True,
) -> Agendamento:
    paciente = db.get(Paciente, dados.paciente_id)
    if paciente is None or not paciente.ativo or paciente.uso_restrito:
        raise RegraNegocio("Paciente inexistente, inativo ou com uso de dados restrito.",
                           campos=[{"campo": "paciente_id", "erro": "inválido"}])
    validar_disponibilidade(db, dados.unidade_id, dados.profissional_id, dados.especialidade_id, dados.data_hora,
                            validar_horario=validar_horario, ignorar_reserva=ignorar_reserva)
    if repo.paciente_ocupado(db, paciente.id, dados.data_hora):
        raise Conflito("O paciente já possui outro agendamento neste mesmo horário.", codigo="PACIENTE_OCUPADO")

    ag = Agendamento(
        numero_agendamento=dados.numero_agendamento or _gerar_numero(),
        data_hora=dados.data_hora,
        status=S.AGENDADO,
        data_criacao=agora(),
        origem=origem_tipo,
        paciente_id=paciente.id,
        profissional_id=dados.profissional_id,
        especialidade_id=dados.especialidade_id,
        unidade_id=dados.unidade_id,
    )
    try:
        with db.begin_nested():  # o índice único parcial é a última barreira contra dupla marcação
            db.add(ag)
            db.flush()
    except IntegrityError as exc:
        raise Conflito("Horário ou número de agendamento já utilizado por outra operação.",
                       codigo="HORARIO_OCUPADO") from exc
    db.add(HistoricoStatusAgendamento(agendamento_id=ag.id, status_anterior=None, status_novo=S.AGENDADO,
                                      data_hora=agora(), origem=origem, motivo=f"criado ({origem_tipo})"))
    auditoria.registrar(db, "AGENDAMENTO_CRIADO", "agendamento", ag.id, origem, usuario_id,
                        {"origem": origem_tipo, "unidade_id": ag.unidade_id, "profissional_id": ag.profissional_id})
    eventos.publicar(eventos.AGENDAMENTO_CRIADO, db=db, agendamento=ag, origem=origem)
    if commit:
        db.commit()
    return ag


def alterar_status(
    db: Session,
    ag: Agendamento,
    novo: StatusAgendamento,
    origem: str,
    motivo: str | None = None,
    usuario_id: int | None = None,
) -> None:
    """Toda transição é validada, registrada no histórico e na auditoria (RF07, RN12)."""
    anterior = ag.status
    if novo == anterior:
        raise RegraNegocio(f"O agendamento já está {anterior.value}.", codigo="TRANSICAO_INVALIDA")
    if novo not in TRANSICOES[anterior]:
        raise RegraNegocio(f"Transição de status inválida: {anterior.value} → {novo.value}.",
                           codigo="TRANSICAO_INVALIDA")
    ag.status = novo
    db.add(HistoricoStatusAgendamento(agendamento_id=ag.id, status_anterior=anterior, status_novo=novo,
                                      data_hora=agora(), origem=origem, motivo=motivo))
    auditoria.registrar(db, "STATUS_AGENDAMENTO_ALTERADO", "agendamento", ag.id, origem, usuario_id,
                        {"de": anterior.value, "para": novo.value})
    db.flush()
    if novo in STATUS_LIBERAM_VAGA:
        eventos.publicar(eventos.VAGA_LIBERADA, db=db, agendamento=ag, origem=origem)


def cancelar(db: Session, agendamento_id: int, motivo: str, usuario) -> Agendamento:
    ag = obter(db, agendamento_id, para_atualizar=True)
    alterar_status(db, ag, S.CANCELADO, auditoria.origem_usuario(usuario), motivo, usuario.id)
    db.commit()
    return ag


def registrar_comparecimento(db: Session, agendamento_id: int, dados: ComparecimentoEntrada, usuario) -> Agendamento:
    ag = obter(db, agendamento_id, para_atualizar=True)
    if ag.data_hora.date() > agora().date():
        raise RegraNegocio("Só é possível registrar comparecimento a partir do dia da consulta.")
    novo = S.REALIZADO if dados.tipo == TipoComparecimento.COMPARECEU else S.FALTA
    origem = auditoria.origem_usuario(usuario)
    alterar_status(db, ag, novo, origem, dados.observacao, usuario.id)
    db.add(HistoricoComparecimento(agendamento_id=ag.id, paciente_id=ag.paciente_id, tipo=dados.tipo,
                                   data_hora=agora(), observacao=dados.observacao, usuario_id=usuario.id))
    db.commit()
    return ag


def listar(db: Session, params: ParamsPaginacao, unidade_id: int | None, data: date | None, inicio, fim,
           especialidade_id, profissional_id, status, paciente_id, busca) -> dict:
    stmt = repo.listar_stmt(unidade_id, data, inicio, fim, especialidade_id, profissional_id, status, paciente_id, busca)
    return paginar(db, stmt, params)


def historico(db: Session, agendamento_id: int) -> list[EventoHistorico]:
    """Linha do tempo com status, mensagens, respostas, remarcações e ofertas (PB18)."""
    from app.modules.confirmacao.models import RespostaConfirmacao
    from app.modules.fila.models import SolicitacaoRemarcacao
    from app.modules.notificacao.models import Mensagem
    from app.modules.recuperacao.models import OfertaVaga, VagaLiberada

    ag = obter(db, agendamento_id)
    ev: list[EventoHistorico] = []
    for h in db.scalars(select(HistoricoStatusAgendamento).where(HistoricoStatusAgendamento.agendamento_id == ag.id)):
        de = h.status_anterior.value if h.status_anterior else "—"
        ev.append(EventoHistorico(data_hora=h.data_hora, tipo="STATUS",
                                  descricao=f"{de} → {h.status_novo.value}" + (f" ({h.motivo})" if h.motivo else ""),
                                  origem=h.origem))
    for m in db.scalars(select(Mensagem).where(Mensagem.agendamento_id == ag.id)):
        ev.append(EventoHistorico(data_hora=m.data_envio or m.data_criacao, tipo="MENSAGEM",
                                  descricao=f"{m.tipo.value}: {m.status.value}" + (f" – {m.motivo}" if m.motivo else ""),
                                  origem="sistema"))
    for r in db.scalars(select(RespostaConfirmacao).where(RespostaConfirmacao.agendamento_id == ag.id)):
        desc = f"Resposta {r.tipo.value}" if r.valida else f"Resposta inválida ({r.motivo_invalidade})"
        ev.append(EventoHistorico(data_hora=r.data_hora, tipo="RESPOSTA", descricao=desc, origem=r.origem))
    for s in db.scalars(select(SolicitacaoRemarcacao).where(SolicitacaoRemarcacao.agendamento_id == ag.id)):
        ev.append(EventoHistorico(data_hora=s.data_resolucao or s.data_solicitacao, tipo="REMARCACAO",
                                  descricao=f"Solicitação de remarcação: {s.status.value}", origem=s.origem))
    vaga = db.scalar(select(VagaLiberada).where(VagaLiberada.agendamento_id == ag.id))
    if vaga is not None:
        ev.append(EventoHistorico(data_hora=vaga.data_liberacao, tipo="VAGA",
                                  descricao=f"Vaga liberada ({vaga.motivo_liberacao}) – situação atual: {vaga.status.value}"))
        for o in db.scalars(select(OfertaVaga).where(OfertaVaga.vaga_id == vaga.id).order_by(OfertaVaga.id)):
            ev.append(EventoHistorico(data_hora=o.data_resposta or o.data_criacao, tipo="OFERTA",
                                      descricao=f"Oferta {o.id} ao paciente {o.paciente_id}: {o.status.value}"))
    for c in db.scalars(select(HistoricoComparecimento).where(HistoricoComparecimento.agendamento_id == ag.id)):
        ev.append(EventoHistorico(data_hora=c.data_hora, tipo="COMPARECIMENTO", descricao=c.tipo.value,
                                  origem=f"usuario:{c.usuario_id}" if c.usuario_id else None))
    return sorted(ev, key=lambda e: e.data_hora)
