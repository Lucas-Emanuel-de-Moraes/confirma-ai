"""Lembretes, processamento de respostas e validação de vínculo (RF05–RF07, RF24, RN03–RN05, RN20, UC03, UC04, UC13)."""

import logging
import unicodedata
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import metricas
from app.core.erros import Conflito, NaoAutorizado
from app.core.relogio import agora
from app.core.telefone import mascarar_telefone, normalizar_telefone
from app.modules.agenda import service as agenda
from app.modules.agenda.models import Agendamento, StatusAgendamento
from app.modules.auditoria import service as auditoria
from app.modules.confirmacao.models import RespostaConfirmacao, TipoResposta
from app.modules.fila import service as fila_service
from app.modules.lgpd import service as lgpd
from app.modules.notificacao import service as notificacao
from app.modules.notificacao.gateway import RespostaRecebida, obter_gateway
from app.modules.notificacao.models import Mensagem, StatusMensagem, TipoMensagem
from app.modules.parametros import service as parametros
from app.modules.recuperacao import service as recuperacao

log = logging.getLogger("confirma_ai.confirmacao")

S = StatusAgendamento

SINONIMOS_LEMBRETE = {
    TipoResposta.SIM: {"SIM", "S", "1", "CONFIRMO", "CONFIRMAR", "OK"},
    TipoResposta.NAO: {"NAO", "N", "2", "NAO VOU", "CANCELAR"},
    TipoResposta.REMARCAR: {"REMARCAR", "3", "REAGENDAR"},
}
SINONIMOS_OFERTA = {
    TipoResposta.ACEITAR: {"ACEITAR", "ACEITO", "SIM", "S", "1"},
    TipoResposta.RECUSAR: {"RECUSAR", "RECUSO", "NAO", "N", "2"},
}
PALAVRAS_SAIR = {"SAIR", "PARAR", "STOP", "DESCADASTRAR"}


def normalizar_texto(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return " ".join(sem_acento.upper().replace("!", " ").replace(".", " ").split())


def interpretar(texto: str, tipo: TipoMensagem) -> TipoResposta | None:
    mapa = SINONIMOS_LEMBRETE if tipo == TipoMensagem.LEMBRETE_CONFIRMACAO else SINONIMOS_OFERTA
    t = normalizar_texto(texto)
    for resposta, sinonimos in mapa.items():
        if t in sinonimos:
            return resposta
    return None


# ====================================================================== UC03 – lembretes
def texto_lembrete(ag: Agendamento) -> str:
    """Mensagem discreta: sem especialidade, procedimento ou dado clínico (seção 5.3, item 8)."""
    primeiro_nome = ag.paciente.nome.split()[0]
    return (
        f"Olá, {primeiro_nome}! Você tem um atendimento agendado na {ag.unidade.nome} "
        f"em {ag.data_hora:%d/%m/%Y} às {ag.data_hora:%H:%M}. "
        "Responda SIM para confirmar, NÃO se não puder comparecer ou REMARCAR para pedir outro horário."
    )


def enviar_lembretes(db: Session) -> dict[str, int]:
    ja_lembrados = select(Mensagem.agendamento_id).where(
        Mensagem.tipo == TipoMensagem.LEMBRETE_CONFIRMACAO, Mensagem.agendamento_id.is_not(None)
    )
    candidatos = db.scalars(
        select(Agendamento).where(
            Agendamento.status == S.AGENDADO,
            Agendamento.data_hora > agora(),
            Agendamento.data_hora <= agora() + timedelta(hours=168),
            Agendamento.id.not_in(ja_lembrados),
        ).order_by(Agendamento.data_hora)
    ).unique().all()
    resultado = {"enfileirados": 0, "bloqueados": 0}
    for ag in candidatos:
        cfg = parametros.vigente(db, ag.unidade_id).parametro
        if ag.data_hora - timedelta(hours=cfg.antecedencia_lembrete_horas) > agora():
            continue  # ainda não chegou a antecedência configurada (RF05)
        expira = min(agora() + timedelta(minutes=cfg.prazo_resposta_min), ag.data_hora)
        msg = notificacao.enfileirar(
            db, tipo=TipoMensagem.LEMBRETE_CONFIRMACAO, paciente=ag.paciente, conteudo=texto_lembrete(ag),
            chave_idempotencia=f"lembrete:{ag.id}", agendamento_id=ag.id, expira_em=expira,
            max_tentativas=cfg.tentativas_contato,
        )
        resultado["bloqueados" if msg.status == StatusMensagem.BLOQUEADA else "enfileirados"] += 1
        db.commit()
    return resultado


def ao_enviar_mensagem(db: Session, mensagem: Mensagem) -> None:
    """AGENDADO → AGUARDANDO_RESPOSTA quando o lembrete chega ao provedor."""
    if mensagem.tipo == TipoMensagem.LEMBRETE_CONFIRMACAO and mensagem.agendamento_id:
        ag = db.get(Agendamento, mensagem.agendamento_id)
        if ag is not None and ag.status == S.AGENDADO:
            agenda.alterar_status(db, ag, S.AGUARDANDO_RESPOSTA, "sistema", "lembrete enviado")


def expirar_sem_resposta(db: Session) -> dict[str, int]:
    """Prazo de resposta esgotado: SEM_RESPOSTA e a vaga entra na recuperação (RF11)."""
    vencidas = db.scalars(
        select(Mensagem).where(
            Mensagem.tipo == TipoMensagem.LEMBRETE_CONFIRMACAO,
            Mensagem.status == StatusMensagem.ENVIADA,
            Mensagem.data_expiracao <= agora(),
        )
    ).all()
    total = 0
    for m in vencidas:
        try:
            m.status = StatusMensagem.EXPIRADA
            ag = agenda.obter(db, m.agendamento_id, para_atualizar=True)
            if ag.status == S.AGUARDANDO_RESPOSTA:
                agenda.alterar_status(db, ag, S.SEM_RESPOSTA, "sistema", "prazo de resposta esgotado")
                total += 1
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
            log.exception("Erro ao expirar lembrete %s", m.id)
    return {"sem_resposta": total}


# ====================================================================== UC13 – validação do vínculo
def _registrar(db: Session, r: RespostaRecebida, tipo: TipoResposta, valida: bool, origem: str,
               mensagem: Mensagem | None = None, motivo: str | None = None) -> RespostaConfirmacao:
    reg = RespostaConfirmacao(
        tipo=tipo, resposta_bruta=(r.texto or "")[:200], identificador_recebido=(r.identificador or "")[:64] or None,
        telefone_origem=r.telefone[:60] if r.telefone else None, valida=valida, motivo_invalidade=motivo,
        data_hora=agora(), origem=origem,
        mensagem_id=mensagem.id if mensagem else None,
        agendamento_id=mensagem.agendamento_id if mensagem else None,
        oferta_id=mensagem.oferta_id if mensagem else None,
    )
    db.add(reg)
    metricas.RESPOSTAS_RECEBIDAS.labels(tipo.value, str(valida).lower()).inc()
    return reg


def _invalida(db: Session, r: RespostaRecebida, origem: str, motivo: str, mensagem: Mensagem | None = None) -> dict:
    """RN20: resposta sem vínculo válido é descartada e registrada, sem alterar a agenda."""
    _registrar(db, r, TipoResposta.INVALIDA, False, origem, mensagem, motivo)
    auditoria.registrar(db, "RESPOSTA_INVALIDA", "mensagem", mensagem.id if mensagem else None, origem,
                        detalhes={"motivo": motivo, "telefone": mascarar_telefone(r.telefone)})
    db.commit()
    return {"valida": False, "motivo": motivo}


def _localizar_mensagem(db: Session, r: RespostaRecebida) -> Mensagem | None:
    if r.identificador:
        return db.scalar(select(Mensagem).where(Mensagem.identificador_unico == r.identificador))
    if r.id_contexto:
        return db.scalar(select(Mensagem).where(Mensagem.id_externo == r.id_contexto))
    return None


def _avisar(db: Session, mensagem: Mensagem, texto: str, sufixo: str) -> None:
    paciente = db.get(Agendamento, mensagem.agendamento_id).paciente if mensagem.agendamento_id else None
    if paciente is None:
        from app.modules.cadastros.models import Paciente

        paciente = db.get(Paciente, mensagem.paciente_id)
    notificacao.enfileirar(db, tipo=TipoMensagem.AVISO, paciente=paciente, conteudo=texto,
                           chave_idempotencia=f"aviso:{mensagem.id}:{sufixo}", com_identificador=False)


def processar_resposta(db: Session, r: RespostaRecebida, origem: str = "webhook") -> dict:
    try:
        telefone = normalizar_telefone(r.telefone)
    except ValueError:
        return _invalida(db, r, origem, "TELEFONE_INVALIDO")
    r.telefone = telefone

    # Revogação pelo próprio paciente (RF21, RN16): "SAIR"
    if normalizar_texto(r.texto) in PALAVRAS_SAIR:
        revogados = lgpd.revogar_por_telefone(db, telefone, f"paciente:{origem}")
        if not revogados:
            return _invalida(db, r, origem, "TELEFONE_DESCONHECIDO")
        _registrar(db, r, TipoResposta.SAIR, True, origem)
        db.commit()
        return {"valida": True, "tipo": "SAIR", "pacientes_afetados": revogados}

    m = _localizar_mensagem(db, r)
    if m is None or m.tipo == TipoMensagem.AVISO or not m.identificador_unico:
        return _invalida(db, r, origem, "IDENTIFICADOR_DESCONHECIDO")
    if m.contato.valor != telefone:
        return _invalida(db, r, origem, "TELEFONE_DIVERGENTE", m)
    if not m.contato.autorizado:
        return _invalida(db, r, origem, "CONTATO_NAO_AUTORIZADO", m)
    if m.status == StatusMensagem.RESPONDIDA:
        return _invalida(db, r, origem, "IDENTIFICADOR_JA_UTILIZADO", m)
    if m.status == StatusMensagem.EXPIRADA or (m.data_expiracao and m.data_expiracao <= agora()):
        return _invalida(db, r, origem, "IDENTIFICADOR_EXPIRADO", m)
    if m.status != StatusMensagem.ENVIADA:
        return _invalida(db, r, origem, "MENSAGEM_NAO_ENVIADA", m)

    tipo = interpretar(r.texto, m.tipo)
    if tipo is None:
        # UC04: opção inválida – pede uma opção válida sem consumir o identificador
        _registrar(db, r, TipoResposta.INVALIDA, False, origem, m, "OPCAO_INVALIDA")
        tentativas = db.query(RespostaConfirmacao).filter(RespostaConfirmacao.mensagem_id == m.id).count()
        opcoes = "SIM, NÃO ou REMARCAR" if m.tipo == TipoMensagem.LEMBRETE_CONFIRMACAO else "ACEITAR ou RECUSAR"
        _avisar(db, m, f"Não entendemos sua resposta. Por favor, responda apenas {opcoes}.", f"opcao{tentativas}")
        db.commit()
        return {"valida": False, "motivo": "OPCAO_INVALIDA"}

    if m.tipo == TipoMensagem.LEMBRETE_CONFIRMACAO:
        return _resposta_lembrete(db, r, m, tipo, origem)
    return _resposta_oferta(db, r, m, tipo, origem)


def _resposta_lembrete(db: Session, r: RespostaRecebida, m: Mensagem, tipo: TipoResposta, origem: str) -> dict:
    ag = agenda.obter(db, m.agendamento_id, para_atualizar=True)
    if ag.status not in (S.AGENDADO, S.AGUARDANDO_RESPOSTA):
        return _invalida(db, r, origem, "AGENDAMENTO_NAO_PENDENTE", m)
    m.status = StatusMensagem.RESPONDIDA  # identificador de uso único (RNF19)
    m.data_resposta = agora()
    _registrar(db, r, tipo, True, origem, m)
    origem_paciente = f"paciente:{origem}"
    if tipo == TipoResposta.SIM:  # RN03
        agenda.alterar_status(db, ag, S.CONFIRMADO, origem_paciente, "paciente respondeu SIM")
        metricas.CONFIRMACOES.inc()
    elif tipo == TipoResposta.NAO:  # RN04 – a vaga se torna candidata à recuperação
        agenda.alterar_status(db, ag, S.NAO_CONFIRMADO, origem_paciente, "paciente respondeu NÃO")
    else:  # RN05 – registra a solicitação sem transferir a vaga
        agenda.alterar_status(db, ag, S.REMARCACAO_SOLICITADA, origem_paciente, "paciente pediu remarcação")
        fila_service.registrar_solicitacao(db, ag, origem_paciente)
    db.commit()
    return {"valida": True, "tipo": tipo.value, "agendamento_id": ag.id, "status": ag.status.value}


def _resposta_oferta(db: Session, r: RespostaRecebida, m: Mensagem, tipo: TipoResposta, origem: str) -> dict:
    origem_paciente = f"paciente:{origem}"
    if tipo == TipoResposta.RECUSAR:
        m.status = StatusMensagem.RESPONDIDA
        m.data_resposta = agora()
        _registrar(db, r, tipo, True, origem, m)
        try:
            recuperacao.recusar_oferta(db, m.oferta_id, origem_paciente)
        except Conflito as exc:
            db.rollback()
            return _invalida(db, r, origem, exc.codigo, m)
        db.commit()
        return {"valida": True, "tipo": tipo.value, "oferta_id": m.oferta_id}
    try:
        novo = recuperacao.aceitar_oferta(db, m.oferta_id, origem_paciente)
    except Conflito as exc:
        # Outra operação venceu a disputa (RF17): nada muda na agenda e o paciente é avisado.
        db.rollback()
        m = db.get(Mensagem, m.id)
        m.status = StatusMensagem.RESPONDIDA
        m.data_resposta = agora()
        _registrar(db, r, TipoResposta.INVALIDA, False, origem, m, exc.codigo)
        _avisar(db, m, "Que pena! Esta vaga não está mais disponível. Você continua na fila de espera.", "indisp")
        db.commit()
        return {"valida": False, "motivo": exc.codigo}
    m.status = StatusMensagem.RESPONDIDA
    m.data_resposta = agora()
    _registrar(db, r, tipo, True, origem, m)
    db.commit()
    return {"valida": True, "tipo": tipo.value, "oferta_id": m.oferta_id, "agendamento_id": novo.id}


# ====================================================================== Webhook
def receber_webhook(db: Session, corpo: bytes, headers: dict[str, str]) -> dict:
    gateway = obter_gateway()
    headers = {k.lower(): v for k, v in headers.items()}
    if not gateway.verificar_assinatura(corpo, headers):
        auditoria.registrar(db, "WEBHOOK_ASSINATURA_INVALIDA", "webhook", origem=f"provedor:{gateway.nome}")
        db.commit()
        raise NaoAutorizado("Assinatura do webhook inválida.", codigo="ASSINATURA_INVALIDA")
    try:
        respostas = gateway.interpretar_webhook(corpo)
    except ValueError:
        return {"processadas": 0, "resultados": [], "erro": "payload inválido"}
    resultados = []
    for r in respostas:
        try:
            resultados.append(processar_resposta(db, r, origem=f"webhook:{gateway.nome}"))
        except Exception:  # noqa: BLE001 – o provedor sempre recebe 200 para não reenviar em loop
            db.rollback()
            log.exception("Erro ao processar resposta do webhook")
            resultados.append({"valida": False, "motivo": "ERRO_INTERNO"})
    return {"processadas": len(resultados), "resultados": resultados}

