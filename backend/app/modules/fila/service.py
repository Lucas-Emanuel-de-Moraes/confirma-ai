"""Fila de espera, disponibilidade para encaixe e remarcações (RF08–RF10, HU02, HU03, RN05)."""

from sqlalchemy.orm import Session

from app.core.erros import Conflito, NaoEncontrado, RegraNegocio
from app.core.paginacao import ParamsPaginacao, paginar
from app.core.relogio import agora
from app.modules.agenda import service as agenda
from app.modules.agenda.models import Agendamento, StatusAgendamento
from app.modules.agenda.schemas import AgendamentoCriar
from app.modules.auditoria import service as auditoria
from app.modules.cadastros.models import Especialidade, Paciente, Profissional, UnidadeSaude
from app.modules.fila import repository as repo
from app.modules.fila.models import FilaEspera, PreferenciaEncaixe, SolicitacaoRemarcacao, StatusRemarcacao
from app.modules.fila.schemas import FilaCriar, PreferenciaEntrada, PreferenciasAtualizar, RemarcacaoResolver


def _preferencias(db: Session, prefs: list[PreferenciaEntrada]) -> list[PreferenciaEncaixe]:
    resultado = []
    for p in prefs:
        if p.unidade_id is not None:
            u = db.get(UnidadeSaude, p.unidade_id)
            if u is None or not u.ativo:
                raise RegraNegocio("Unidade da preferência inexistente ou inativa.",
                                   campos=[{"campo": "preferencias.unidade_id", "erro": "inválida"}])
        resultado.append(PreferenciaEncaixe(**p.model_dump()))
    return resultado


def adicionar(db: Session, dados: FilaCriar, usuario, origem: str | None = None, agendamento_origem_id=None,
              commit: bool = True) -> FilaEspera:
    origem = origem or auditoria.origem_usuario(usuario)
    paciente = db.get(Paciente, dados.paciente_id)
    if paciente is None or not paciente.ativo or paciente.uso_restrito:
        raise RegraNegocio("Paciente inexistente, inativo ou com uso de dados restrito.")
    esp = db.get(Especialidade, dados.especialidade_id)
    if esp is None or not esp.ativo:
        raise RegraNegocio("Especialidade inexistente ou inativa.")
    if dados.profissional_id is not None:
        prof = db.get(Profissional, dados.profissional_id)
        if prof is None or not prof.ativo or not prof.possui_especialidade(esp.id):
            raise RegraNegocio("Profissional inexistente, inativo ou sem esta especialidade.")
    if repo.entrada_ativa(db, paciente.id, esp.id):
        raise Conflito("O paciente já está na fila desta especialidade.", codigo="JA_NA_FILA")
    entrada = FilaEspera(
        paciente_id=paciente.id,
        especialidade_id=esp.id,
        profissional_id=dados.profissional_id,
        data_entrada=agora(),
        prioridade=dados.prioridade or paciente.prioridade_assistencial,
        disponivel_para_encaixe=dados.disponivel_para_encaixe,
        ativo=True,
        observacao=dados.observacao,
        agendamento_origem_id=agendamento_origem_id,
        preferencias=_preferencias(db, dados.preferencias),
    )
    db.add(entrada)
    db.flush()
    auditoria.registrar(db, "FILA_ENTRADA", "fila_espera", entrada.id, origem, getattr(usuario, "id", None),
                        {"paciente_id": paciente.id, "especialidade_id": esp.id, "prioridade": entrada.prioridade.value})
    if commit:
        db.commit()
    return entrada


def obter(db: Session, fila_id: int) -> FilaEspera:
    entrada = db.get(FilaEspera, fila_id)
    if entrada is None:
        raise NaoEncontrado("Entrada da fila não encontrada.")
    return entrada


def atualizar_preferencias(db: Session, fila_id: int, dados: PreferenciasAtualizar, usuario) -> FilaEspera:
    entrada = obter(db, fila_id)
    if not entrada.ativo:
        raise RegraNegocio("Esta entrada da fila já foi encerrada.")
    entrada.disponivel_para_encaixe = dados.disponivel_para_encaixe
    entrada.preferencias = _preferencias(db, dados.preferencias)
    auditoria.registrar(db, "FILA_PREFERENCIAS_ALTERADAS", "fila_espera", entrada.id,
                        auditoria.origem_usuario(usuario), usuario.id,
                        {"disponivel": dados.disponivel_para_encaixe, "qtd_preferencias": len(dados.preferencias)})
    db.commit()
    return entrada


def remover(db: Session, fila_id: int, motivo: str, usuario) -> FilaEspera:
    entrada = obter(db, fila_id)
    encerrar(entrada, motivo)
    auditoria.registrar(db, "FILA_SAIDA", "fila_espera", entrada.id, auditoria.origem_usuario(usuario),
                        usuario.id, {"motivo": motivo})
    db.commit()
    return entrada


def encerrar(entrada: FilaEspera, motivo: str) -> None:
    entrada.ativo = False
    entrada.data_saida = agora()
    entrada.motivo_saida = motivo[:80]


def listar(db: Session, params: ParamsPaginacao, **filtros) -> dict:
    return paginar(db, repo.listar_stmt(**filtros), params)


# ====================================================================== Remarcações (HU02)
def registrar_solicitacao(db: Session, ag: Agendamento, origem: str) -> SolicitacaoRemarcacao:
    """RN05: registra o pedido sem transferir a vaga; a recepção trata a pendência."""
    existente = repo.remarcacao_pendente_do_agendamento(db, ag.id)
    if existente:
        return existente
    s = SolicitacaoRemarcacao(agendamento_id=ag.id, data_solicitacao=agora(), origem=origem,
                              status=StatusRemarcacao.PENDENTE)
    db.add(s)
    db.flush()
    auditoria.registrar(db, "REMARCACAO_SOLICITADA", "agendamento", ag.id, origem)
    return s


def listar_remarcacoes(db: Session, params: ParamsPaginacao, status: StatusRemarcacao | None) -> dict:
    pagina = paginar(db, repo.remarcacoes_stmt(status), params)
    pagina["itens"] = [
        {**{c: getattr(s, c) for c in ("id", "agendamento_id", "data_solicitacao", "origem", "status",
                                       "data_resolucao", "observacao", "novo_agendamento_id")},
         "agendamento": db.get(Agendamento, s.agendamento_id)}
        for s in pagina["itens"]
    ]
    return pagina


def resolver_remarcacao(db: Session, solicitacao_id: int, dados: RemarcacaoResolver, usuario) -> SolicitacaoRemarcacao:
    s = db.get(SolicitacaoRemarcacao, solicitacao_id)
    if s is None:
        raise NaoEncontrado("Solicitação de remarcação não encontrada.")
    if s.status != StatusRemarcacao.PENDENTE:
        raise Conflito("Esta solicitação já foi tratada.", codigo="JA_TRATADA")
    ag = agenda.obter(db, s.agendamento_id, para_atualizar=True)
    origem = auditoria.origem_usuario(usuario)

    if dados.acao == "REMARCAR":
        novo = agenda.criar(
            db,
            AgendamentoCriar(paciente_id=ag.paciente_id, unidade_id=ag.unidade_id, especialidade_id=ag.especialidade_id,
                             profissional_id=dados.novo_profissional_id or ag.profissional_id,
                             data_hora=dados.nova_data_hora),
            origem, usuario.id, origem_tipo="remarcacao", commit=False,
        )
        # Só agora, com a nova condição registrada, o original é cancelado e a vaga é liberada (RF08)
        agenda.alterar_status(db, ag, StatusAgendamento.CANCELADO, origem,
                              f"remarcado para o agendamento {novo.numero_agendamento}", usuario.id)
        s.status = StatusRemarcacao.REMARCADA
        s.novo_agendamento_id = novo.id
    elif dados.acao == "MANTER":
        agenda.alterar_status(db, ag, StatusAgendamento.CONFIRMADO, origem, "paciente manteve a consulta", usuario.id)
        s.status = StatusRemarcacao.MANTIDA
    else:
        agenda.alterar_status(db, ag, StatusAgendamento.CANCELADO, origem, "remarcação não realizada", usuario.id)
        s.status = StatusRemarcacao.CANCELADA
        if dados.incluir_fila_espera and not repo.entrada_ativa(db, ag.paciente_id, ag.especialidade_id):
            adicionar(
                db,
                FilaCriar(paciente_id=ag.paciente_id, especialidade_id=ag.especialidade_id,
                          preferencias=[PreferenciaEntrada(unidade_id=ag.unidade_id)]),
                usuario, origem, agendamento_origem_id=ag.id, commit=False,
            )
    s.data_resolucao = agora()
    s.observacao = dados.observacao
    s.resolvido_por_id = usuario.id
    auditoria.registrar(db, "REMARCACAO_RESOLVIDA", "solicitacao_remarcacao", s.id, origem, usuario.id,
                        {"acao": dados.acao})
    db.commit()
    return s
