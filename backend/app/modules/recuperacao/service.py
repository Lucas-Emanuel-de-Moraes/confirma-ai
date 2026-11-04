"""Recuperação de vagas: identificação, elegibilidade, priorização, oferta, reserva e aceite atômico.

Requisitos: RF11–RF17, RN02, RN06–RN14, UC05–UC07, RNF03.
"""

import logging
from datetime import timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import metricas
from app.core.erros import Conflito, NaoEncontrado, RegraNegocio
from app.core.paginacao import ParamsPaginacao, paginar
from app.core.relogio import agora
from app.modules.agenda import repository as agenda_repo
from app.modules.agenda import service as agenda
from app.modules.agenda.models import Agendamento
from app.modules.agenda.schemas import AgendamentoCriar
from app.modules.auditoria import service as auditoria
from app.modules.cadastros import repository as cad_repo
from app.modules.cadastros.models import PESO_PRIORIDADE, Profissional, UnidadeSaude
from app.modules.fila import service as fila_service
from app.modules.fila.models import FilaEspera
from app.modules.notificacao import service as notificacao
from app.modules.notificacao.models import Mensagem, StatusMensagem, TipoMensagem
from app.modules.parametros import service as parametros
from app.modules.parametros.models import RegraElegibilidade
from app.modules.recuperacao import repository as repo
from app.modules.recuperacao.models import OfertaVaga, StatusOferta, StatusVaga, VagaLiberada

log = logging.getLogger("confirma_ai.recuperacao")


# ====================================================================== Identificar vaga (UC05, RF11)
def liberar_vaga(db: Session, agendamento: Agendamento, origem: str) -> VagaLiberada | None:
    """Chamado quando um agendamento passa a NAO_CONFIRMADO, CANCELADO ou SEM_RESPOSTA."""
    if repo.vaga_do_agendamento(db, agendamento.id) is not None:
        return None
    cfg = parametros.vigente(db, agendamento.unidade_id)
    vaga = VagaLiberada(
        agendamento_id=agendamento.id,
        unidade_id=agendamento.unidade_id,
        profissional_id=agendamento.profissional_id,
        especialidade_id=agendamento.especialidade_id,
        data_hora=agendamento.data_hora,
        status=StatusVaga.DISPONIVEL,
        motivo_liberacao=agendamento.status.value,
        data_liberacao=agora(),
    )
    limite = agendamento.data_hora - timedelta(minutes=cfg.parametro.antecedencia_minima_oferta_min)
    if agora() >= limite:
        vaga.status = StatusVaga.ENCERRADA
        vaga.observacao = "Liberada fora da janela de reaproveitamento"
    db.add(vaga)
    db.flush()
    auditoria.registrar(db, "VAGA_LIBERADA", "vaga_liberada", vaga.id, origem,
                        detalhes={"agendamento_id": agendamento.id, "motivo": vaga.motivo_liberacao,
                                  "status": vaga.status.value})
    if vaga.status == StatusVaga.DISPONIVEL:
        metricas.VAGAS_LIBERADAS.inc()
        ofertar_proximo(db, vaga.id, origem)
    return vaga


# ====================================================================== Elegibilidade (RF12, RN06–RN08, RN14)
def compativel_com_profissional(fila: FilaEspera, vaga: VagaLiberada, unidade: UnidadeSaude,
                                regra: RegraElegibilidade) -> bool:
    if unidade.exige_profissional_especifico:
        return fila.profissional_id == vaga.profissional_id
    if fila.profissional_id is None or fila.profissional_id == vaga.profissional_id:
        return True
    # O paciente pediu outro profissional: só aceita equivalente se a unidade permitir explicitamente (RN08)
    return unidade.permite_profissional_equivalente and not regra.exige_profissional_compativel


def selecionar_elegiveis(db: Session, vaga: VagaLiberada) -> list[tuple[FilaEspera, str]]:
    """Devolve os elegíveis já ordenados (RF13, RN09, RN10) com o critério usado, para rastreabilidade."""
    cfg = parametros.vigente(db, vaga.unidade_id)
    regra = cfg.regra
    unidade = db.get(UnidadeSaude, vaga.unidade_id)
    liberou = db.get(Agendamento, vaga.agendamento_id)
    candidatos = []
    for f in repo.candidatos_da_fila(db, vaga, liberou.paciente_id):
        if not f.paciente.contato_autorizado:  # RN06, RN16
            continue
        if not compativel_com_profissional(f, vaga, unidade, regra):  # RN08
            continue
        if not any(p.is_compativel(vaga.unidade_id, vaga.data_hora) for p in f.preferencias):  # RN07
            continue
        candidatos.append(f)

    def chave(f: FilaEspera):
        prioridade = -PESO_PRIORIDADE[f.prioridade] if regra.considera_prioridade_assistencial else 0
        desempate = f.data_entrada if regra.criterio_desempate == "DATA_ENTRADA" else f.id
        return (prioridade, desempate, f.id)  # sempre determinístico (RN10)

    candidatos.sort(key=chave)
    total = len(candidatos)
    return [
        (f, (f"regra v{regra.versao}; prioridade="
             f"{f.prioridade.value if regra.considera_prioridade_assistencial else 'não considerada'}; "
             f"entrada={f.data_entrada:%Y-%m-%d %H:%M}; fila_id={f.id}; posição {i + 1} de {total}"))
        for i, f in enumerate(candidatos)
    ]


def _motivo_para_encerrar(db: Session, vaga: VagaLiberada, cfg) -> str | None:
    if agora() >= vaga.data_hora - timedelta(minutes=cfg.parametro.antecedencia_minima_oferta_min):
        return "Fora da janela de reaproveitamento"
    prof = db.get(Profissional, vaga.profissional_id)
    if prof is None or not prof.ativo:
        return "Profissional indisponível"
    if cad_repo.bloqueio_vigente(db, vaga.unidade_id, vaga.profissional_id, vaga.data_hora):
        return "Agenda bloqueada (RN14)"
    if agenda_repo.ocupante_do_horario(db, vaga.profissional_id, vaga.data_hora):
        return "Horário ocupado por outro agendamento"
    return None


# ====================================================================== Ofertar (UC06, RF14, RF15)
def ofertar_proximo(db: Session, vaga_id: int, origem: str = auditoria.ORIGEM_SISTEMA) -> OfertaVaga | None:
    vaga = repo.vaga_para_atualizar(db, vaga_id)  # bloqueia a linha da vaga durante a seleção
    if vaga is None or vaga.status not in (StatusVaga.DISPONIVEL, StatusVaga.SEM_ELEGIVEIS):
        return None
    cfg = parametros.vigente(db, vaga.unidade_id)
    motivo = _motivo_para_encerrar(db, vaga, cfg)
    if motivo:
        vaga.status = StatusVaga.ENCERRADA
        vaga.observacao = motivo
        auditoria.registrar(db, "VAGA_ENCERRADA", "vaga_liberada", vaga.id, origem, detalhes={"motivo": motivo})
        db.flush()
        return None

    unidade = db.get(UnidadeSaude, vaga.unidade_id)
    prof = db.get(Profissional, vaga.profissional_id)
    for fila, criterio in selecionar_elegiveis(db, vaga):
        prazo = min(agora() + timedelta(minutes=cfg.parametro.janela_reserva_min), vaga.data_hora)
        oferta = OfertaVaga(
            vaga_id=vaga.id, agendamento_id=vaga.agendamento_id, paciente_id=fila.paciente_id, fila_id=fila.id,
            vaga_data_hora=vaga.data_hora, status=StatusOferta.RESERVADA, prazo_resposta=prazo,
            reserva_ativa=True, data_criacao=agora(), criterio_selecao=criterio[:300],
        )
        try:
            with db.begin_nested():  # índice único parcial: no máximo uma reserva ativa por vaga
                db.add(oferta)
                db.flush()
        except IntegrityError:
            log.info("Vaga %s já possui reserva ativa (concorrência).", vaga.id)
            return None
        vaga.status = StatusVaga.EM_OFERTA
        primeiro_nome = fila.paciente.nome.split()[0]
        texto = (
            f"Olá, {primeiro_nome}! Surgiu uma vaga de {fila.especialidade.nome} com {prof.nome} "
            f"na {unidade.nome}, em {vaga.data_hora:%d/%m/%Y} às {vaga.data_hora:%H:%M}. "
            f"Responda ACEITAR para ficar com a vaga ou RECUSAR. "
            f"Ela fica reservada para você até {prazo:%d/%m às %H:%M}."
        )
        msg = notificacao.enfileirar(
            db, tipo=TipoMensagem.OFERTA_ENCAIXE, paciente=fila.paciente, conteudo=texto,
            chave_idempotencia=f"oferta:{oferta.id}", oferta_id=oferta.id, expira_em=prazo,
            max_tentativas=cfg.parametro.tentativas_contato,
        )
        if msg.status == StatusMensagem.BLOQUEADA:
            oferta.status = StatusOferta.FALHA_CONTATO
            oferta.reserva_ativa = False
            oferta.motivo = "Contato não autorizado"
            vaga.status = StatusVaga.DISPONIVEL
            db.flush()
            continue
        auditoria.registrar(db, "OFERTA_CRIADA", "oferta_vaga", oferta.id, origem,
                            detalhes={"vaga_id": vaga.id, "paciente_id": fila.paciente_id, "criterio": criterio})
        db.flush()
        return oferta

    if vaga.status != StatusVaga.SEM_ELEGIVEIS:
        vaga.status = StatusVaga.SEM_ELEGIVEIS
        vaga.observacao = "Nenhum paciente elegível na fila – disponível para ação manual"
        auditoria.registrar(db, "VAGA_SEM_ELEGIVEIS", "vaga_liberada", vaga.id, origem)
    db.flush()
    return None


# ====================================================================== Aceite atômico (UC07, RF17, RN13)
def aceitar_oferta(db: Session, oferta_id: int, origem: str, usuario_id: int | None = None) -> Agendamento:
    """Confirma o encaixe numa única transação com bloqueio de linha. A operação perdedora recebe 409."""
    oferta = repo.oferta_para_atualizar(db, oferta_id)
    if oferta is None:
        raise NaoEncontrado("Oferta não encontrada.")
    if oferta.status != StatusOferta.RESERVADA:
        raise Conflito(f"Esta oferta não está mais disponível ({oferta.status.value}).", codigo="OFERTA_INDISPONIVEL")
    if agora() > oferta.prazo_resposta:
        raise Conflito("O prazo para aceitar esta oferta terminou.", codigo="OFERTA_EXPIRADA")
    vaga = repo.vaga_para_atualizar(db, oferta.vaga_id)
    if vaga.status != StatusVaga.EM_OFERTA:
        raise Conflito("A vaga não está mais reservada para esta oferta.", codigo="VAGA_INDISPONIVEL")
    fila = db.get(FilaEspera, oferta.fila_id)
    novo = agenda.criar(
        db,
        AgendamentoCriar(paciente_id=oferta.paciente_id, unidade_id=vaga.unidade_id,
                         especialidade_id=vaga.especialidade_id, profissional_id=vaga.profissional_id,
                         data_hora=vaga.data_hora),
        origem, usuario_id, origem_tipo="encaixe", validar_horario=False, ignorar_reserva=True, commit=False,
    )
    oferta.status = StatusOferta.ACEITA
    oferta.reserva_ativa = False
    oferta.data_resposta = agora()
    oferta.agendamento_gerado_id = novo.id
    vaga.status = StatusVaga.PREENCHIDA
    vaga.data_preenchimento = agora()
    vaga.agendamento_novo_id = novo.id
    if fila is not None and fila.ativo:
        fila_service.encerrar(fila, "ENCAIXE_CONFIRMADO")
    auditoria.registrar(db, "ENCAIXE_CONFIRMADO", "oferta_vaga", oferta.id, origem, usuario_id,
                        {"vaga_id": vaga.id, "agendamento_novo_id": novo.id})
    metricas.VAGAS_RECUPERADAS.inc()
    db.flush()
    return novo


def _liberar_reserva(db: Session, oferta: OfertaVaga, status: StatusOferta, motivo: str, origem: str,
                     reofertar: bool = True, usuario_id: int | None = None) -> None:
    """RF16: libera a reserva e, quando aplicável, oferece ao próximo da fila."""
    oferta.status = status
    oferta.reserva_ativa = False
    oferta.data_resposta = agora()
    oferta.motivo = motivo
    for m in db.query(Mensagem).filter(Mensagem.oferta_id == oferta.id,
                                       Mensagem.status.in_([StatusMensagem.PENDENTE, StatusMensagem.ENVIADA])):
        notificacao.cancelar_mensagem(
            db, m, motivo, StatusMensagem.EXPIRADA if status == StatusOferta.EXPIRADA else StatusMensagem.CANCELADA
        )
    vaga = repo.vaga_para_atualizar(db, oferta.vaga_id)
    auditoria.registrar(db, f"OFERTA_{status.value}", "oferta_vaga", oferta.id, origem, usuario_id, {"motivo": motivo})
    if vaga.status == StatusVaga.EM_OFERTA:
        vaga.status = StatusVaga.DISPONIVEL if reofertar else StatusVaga.ENCERRADA
        if not reofertar:
            vaga.observacao = "Encerrada para tratamento manual"
    db.flush()
    if reofertar:
        ofertar_proximo(db, vaga.id, origem)


def recusar_oferta(db: Session, oferta_id: int, origem: str, usuario_id: int | None = None) -> OfertaVaga:
    oferta = repo.oferta_para_atualizar(db, oferta_id)
    if oferta is None:
        raise NaoEncontrado("Oferta não encontrada.")
    if oferta.status != StatusOferta.RESERVADA:
        raise Conflito(f"Esta oferta não está mais disponível ({oferta.status.value}).", codigo="OFERTA_INDISPONIVEL")
    _liberar_reserva(db, oferta, StatusOferta.RECUSADA, "Recusada pelo paciente", origem, usuario_id=usuario_id)
    return oferta


def cancelar_oferta(db: Session, oferta_id: int, motivo: str, reofertar: bool, usuario) -> OfertaVaga:
    oferta = repo.oferta_para_atualizar(db, oferta_id)
    if oferta is None:
        raise NaoEncontrado("Oferta não encontrada.")
    if oferta.status != StatusOferta.RESERVADA:
        raise Conflito("Só é possível cancelar uma oferta com reserva ativa.", codigo="OFERTA_INDISPONIVEL")
    _liberar_reserva(db, oferta, StatusOferta.CANCELADA, motivo, auditoria.origem_usuario(usuario), reofertar,
                     usuario.id)
    db.commit()
    return oferta


def aceitar_manual(db: Session, oferta_id: int, usuario) -> Agendamento:
    """Aceite registrado pela recepção (ex.: paciente ligou) – alternativa manual da seção 8.3."""
    novo = aceitar_oferta(db, oferta_id, auditoria.origem_usuario(usuario), usuario.id)
    db.commit()
    return novo


def recusar_manual(db: Session, oferta_id: int, usuario) -> OfertaVaga:
    oferta = recusar_oferta(db, oferta_id, auditoria.origem_usuario(usuario), usuario.id)
    db.commit()
    return oferta


def ofertar_manual(db: Session, vaga_id: int, usuario) -> VagaLiberada:
    vaga = repo.vaga_para_atualizar(db, vaga_id)
    if vaga is None:
        raise NaoEncontrado("Vaga não encontrada.")
    if vaga.status in (StatusVaga.EM_OFERTA, StatusVaga.PREENCHIDA):
        raise Conflito(f"A vaga está {vaga.status.value}.", codigo="VAGA_INDISPONIVEL")
    if vaga.data_hora <= agora():
        raise RegraNegocio("O horário desta vaga já passou.")
    vaga.status = StatusVaga.DISPONIVEL
    db.flush()
    ofertar_proximo(db, vaga.id, auditoria.origem_usuario(usuario))
    db.commit()
    return vaga


# ====================================================================== Tarefas periódicas (RN11, RF16)
def expirar_ofertas(db: Session) -> dict[str, int]:
    expiradas = 0
    for oferta_id in repo.ofertas_reservadas_vencidas(db, agora()):
        try:
            oferta = repo.oferta_para_atualizar(db, oferta_id)
            if oferta and oferta.status == StatusOferta.RESERVADA and oferta.prazo_resposta <= agora():
                _liberar_reserva(db, oferta, StatusOferta.EXPIRADA, "Prazo de resposta vencido", auditoria.ORIGEM_SISTEMA)
                expiradas += 1
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
            log.exception("Erro ao expirar oferta %s", oferta_id)
    reavaliadas = 0
    for vaga_id in repo.vagas_a_reavaliar(db, agora()):
        try:
            if ofertar_proximo(db, vaga_id):
                reavaliadas += 1
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
            log.exception("Erro ao reavaliar vaga %s", vaga_id)
    return {"ofertas_expiradas": expiradas, "novas_ofertas": reavaliadas}


# ====================================================================== Reações a eventos de outros módulos
def ao_criar_agendamento(db: Session, agendamento: Agendamento, origem: str) -> None:
    """Se a recepção ocupou manualmente um horário liberado, a vaga conta como recuperada."""
    if agendamento.origem == "encaixe":
        return
    vaga = repo.vaga_no_horario(db, agendamento.profissional_id, agendamento.data_hora)
    if vaga is not None and vaga.agendamento_id != agendamento.id:
        vaga.status = StatusVaga.PREENCHIDA
        vaga.data_preenchimento = agora()
        vaga.agendamento_novo_id = agendamento.id
        vaga.observacao = "Preenchida manualmente pela recepção"
        metricas.VAGAS_RECUPERADAS.inc()
        auditoria.registrar(db, "VAGA_PREENCHIDA_MANUALMENTE", "vaga_liberada", vaga.id, origem)


def ao_enviar_mensagem(db: Session, mensagem: Mensagem) -> None:
    if mensagem.oferta_id:
        oferta = db.get(OfertaVaga, mensagem.oferta_id)
        if oferta is not None:
            oferta.data_envio = mensagem.data_envio


def ao_falhar_mensagem(db: Session, mensagem: Mensagem) -> None:
    """Falha definitiva de contato libera a reserva e reoferta (RF16)."""
    if not mensagem.oferta_id:
        return
    oferta = repo.oferta_para_atualizar(db, mensagem.oferta_id)
    if oferta is not None and oferta.status == StatusOferta.RESERVADA:
        _liberar_reserva(db, oferta, StatusOferta.FALHA_CONTATO, mensagem.motivo or "Falha de contato",
                         auditoria.ORIGEM_SISTEMA)


def ao_revogar_autorizacao(db: Session, paciente_id: int, origem: str) -> None:
    for oferta_id in repo.ofertas_reservadas_do_paciente(db, paciente_id):
        oferta = repo.oferta_para_atualizar(db, oferta_id)
        if oferta is not None and oferta.status == StatusOferta.RESERVADA:
            _liberar_reserva(db, oferta, StatusOferta.CANCELADA, "Autorização de contato revogada", origem)


# ====================================================================== Consultas
def listar_vagas(db: Session, params: ParamsPaginacao, **filtros) -> dict:
    return paginar(db, repo.listar_vagas_stmt(**filtros), params)


def obter_vaga(db: Session, vaga_id: int) -> VagaLiberada:
    vaga = db.get(VagaLiberada, vaga_id)
    if vaga is None:
        raise NaoEncontrado("Vaga não encontrada.")
    return vaga


def listar_ofertas(db: Session, params: ParamsPaginacao, **filtros) -> dict:
    return paginar(db, repo.listar_ofertas_stmt(**filtros), params)
