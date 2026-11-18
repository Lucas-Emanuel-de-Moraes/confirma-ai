"""Consentimento, direitos do titular e retenção de dados (RF21–RF23, RN15–RN19, HU04, UC11, UC12)."""

from datetime import timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core import eventos
from app.core.erros import Conflito, NaoEncontrado, RegraNegocio
from app.core.paginacao import ParamsPaginacao, paginar
from app.core.relogio import agora
from app.core.telefone import mascarar_telefone
from app.modules.agenda.models import Agendamento
from app.modules.auditoria import service as auditoria
from app.modules.cadastros import repository as cad_repo
from app.modules.cadastros import service as cadastros
from app.modules.cadastros.models import Contato, Paciente
from app.modules.cadastros.schemas import PacienteAtualizar
from app.modules.confirmacao.models import RespostaConfirmacao
from app.modules.fila.models import FilaEspera
from app.modules.lgpd import consentimento
from app.modules.lgpd.models import (
    AcaoConsentimento,
    AcaoRetencao,
    CategoriaDado,
    HistoricoConsentimento,
    PoliticaRetencao,
    RequisicaoTitular,
    StatusRequisicao,
    TipoRequisicaoTitular,
)
from app.modules.lgpd.schemas import AutorizacaoEntrada, PoliticaAtualizar, RequisicaoCriar, RequisicaoResolver
from app.modules.notificacao import service as notificacao
from app.modules.notificacao.models import Mensagem
from app.modules.recuperacao.models import OfertaVaga


# ====================================================================== HU04 – autorização de contato
def _contato(paciente: Paciente) -> Contato:
    c = paciente.contato_principal
    if c is None:
        raise RegraNegocio("Paciente sem contato cadastrado.")
    return c


def autorizar(db: Session, paciente_id: int, dados: AutorizacaoEntrada, usuario) -> Paciente:
    paciente = cadastros.obter_paciente(db, paciente_id)
    if not paciente.ativo or paciente.uso_restrito:
        raise RegraNegocio("Paciente inativo ou com uso de dados restrito não pode autorizar contato.")
    contato = _contato(paciente)
    origem = f"{dados.origem}:{auditoria.origem_usuario(usuario)}"[:80]
    consentimento.autorizar_contato(db, contato, origem, dados.preferencias)
    auditoria.registrar(db, "CONTATO_AUTORIZADO", "paciente", paciente.id, origem, usuario.id)
    db.commit()
    return paciente


def _revogar(db: Session, paciente: Paciente, origem: str, motivo: str | None) -> None:
    """RN16: efeito imediato – cancela mensagens na fila e reservas de encaixe em aberto."""
    contato = _contato(paciente)
    if contato.autorizado:
        consentimento.revogar_contato(db, contato, origem, motivo)
    canceladas = notificacao.cancelar_pendentes_do_paciente(db, paciente.id, "Autorização revogada")
    auditoria.registrar(db, "CONTATO_REVOGADO", "paciente", paciente.id, origem[:80],
                        detalhes={"mensagens_canceladas": canceladas})
    db.flush()
    eventos.publicar(eventos.AUTORIZACAO_REVOGADA, db=db, paciente_id=paciente.id, origem=origem[:80])


def revogar(db: Session, paciente_id: int, motivo: str | None, usuario) -> Paciente:
    paciente = cadastros.obter_paciente(db, paciente_id)
    _revogar(db, paciente, auditoria.origem_usuario(usuario), motivo)
    db.commit()
    return paciente


def revogar_por_telefone(db: Session, telefone: str, origem: str) -> int:
    """Paciente respondeu SAIR pelo WhatsApp."""
    total = 0
    for contato in cad_repo.contato_por_telefone(db, telefone):
        if contato.autorizado:
            _revogar(db, contato.paciente, origem, "solicitado pelo paciente por mensagem")
            total += 1
    return total


def atualizar_preferencias(db: Session, paciente_id: int, preferencias: dict, usuario) -> Paciente:
    paciente = cadastros.obter_paciente(db, paciente_id)
    contato = _contato(paciente)
    contato.preferencias = preferencias
    contato.origem_alteracao = auditoria.origem_usuario(usuario)
    consentimento.registrar_historico(db, contato, AcaoConsentimento.PREFERENCIAS, contato.origem_alteracao,
                                      {"preferencias": preferencias})
    db.commit()
    return paciente


def consultar_consentimento(db: Session, paciente_id: int) -> dict:
    paciente = cadastros.obter_paciente(db, paciente_id)
    contato = _contato(paciente)
    historico = db.scalars(
        select(HistoricoConsentimento).where(HistoricoConsentimento.paciente_id == paciente.id)
        .order_by(HistoricoConsentimento.id)
    ).all()
    return {
        "paciente_id": paciente.id, "autorizado": contato.autorizado, "data_autorizacao": contato.data_autorizacao,
        "data_revogacao": contato.data_revogacao, "origem_alteracao": contato.origem_alteracao,
        "preferencias": contato.preferencias, "historico": historico,
    }


# ====================================================================== UC11 – requisições do titular
def criar_requisicao(db: Session, dados: RequisicaoCriar, usuario) -> RequisicaoTitular:
    cadastros.obter_paciente(db, dados.paciente_id)
    req = RequisicaoTitular(
        paciente_id=dados.paciente_id, tipo=dados.tipo, canal=dados.canal, status=StatusRequisicao.ABERTA,
        dados_correcao=dados.dados_correcao.model_dump(exclude_none=True) if dados.dados_correcao else None,
        data_solicitacao=agora(), registrado_por_id=usuario.id,
    )
    db.add(req)
    db.flush()
    auditoria.registrar(db, "REQUISICAO_TITULAR_REGISTRADA", "requisicao_titular", req.id,
                        auditoria.origem_usuario(usuario), usuario.id, {"tipo": dados.tipo.value})
    db.commit()
    return req


def relatorio_dados(db: Session, paciente: Paciente) -> dict:
    """Dados pessoais tratados sobre o titular (requisição de acesso)."""
    agendamentos = db.scalars(select(Agendamento).where(Agendamento.paciente_id == paciente.id)
                              .order_by(Agendamento.data_hora)).unique().all()
    filas = db.scalars(select(FilaEspera).where(FilaEspera.paciente_id == paciente.id)).unique().all()
    consent = consultar_consentimento(db, paciente.id)
    n_msgs = db.query(Mensagem).filter(Mensagem.paciente_id == paciente.id).count()
    return {
        "gerado_em": agora().isoformat(),
        "controlador": "Unidade de saúde responsável pelo atendimento",
        "finalidade": "Gestão de agenda, confirmação de consultas e oferta de encaixes",
        "paciente": {"id": paciente.id, "nome": paciente.nome, "ativo": paciente.ativo,
                     "prioridade_assistencial": paciente.prioridade_assistencial.value,
                     "data_cadastro": paciente.data_cadastro.isoformat()},
        "contatos": [{"tipo": c.tipo.value, "valor": c.valor, "autorizado": c.autorizado,
                      "preferencias": c.preferencias} for c in paciente.contatos],
        "consentimento": [{"acao": h.acao.value, "data_hora": h.data_hora.isoformat(), "origem": h.origem}
                          for h in consent["historico"]],
        "agendamentos": [{"numero": a.numero_agendamento, "data_hora": a.data_hora.isoformat(),
                          "status": a.status.value, "unidade": a.unidade.nome,
                          "especialidade": a.especialidade.nome} for a in agendamentos],
        "fila_espera": [{"especialidade": f.especialidade.nome, "data_entrada": f.data_entrada.isoformat(),
                         "ativo": f.ativo, "disponivel_para_encaixe": f.disponivel_para_encaixe} for f in filas],
        "mensagens_trocadas": n_msgs,
    }


def anonimizar_paciente(db: Session, paciente: Paciente, origem: str) -> None:
    paciente.nome = f"Paciente anonimizado #{paciente.id}"
    paciente.anonimizado = True
    paciente.uso_restrito = True
    paciente.ativo = False
    paciente.data_inativacao = paciente.data_inativacao or agora()
    for c in paciente.contatos:
        c.valor = f"anon-{paciente.id}-{c.id}"
        c.autorizado = False
        c.preferencias = None
    auditoria.registrar(db, "PACIENTE_ANONIMIZADO", "paciente", paciente.id, origem)


def _possui_registros_obrigatorios(db: Session, paciente_id: int) -> bool:
    """Agendamentos, ofertas e mensagens comprovam confirmações e transições (RN18)."""
    return any(
        db.scalar(select(m.id).where(m.paciente_id == paciente_id).limit(1)) is not None
        for m in (Agendamento, OfertaVaga, Mensagem)
    )


def resolver_requisicao(db: Session, req_id: int, dados: RequisicaoResolver, usuario) -> dict:
    req = db.get(RequisicaoTitular, req_id)
    if req is None:
        raise NaoEncontrado("Requisição não encontrada.")
    if req.status != StatusRequisicao.ABERTA:
        raise Conflito("Requisição já resolvida.", codigo="JA_RESOLVIDA")
    paciente = cadastros.obter_paciente(db, req.paciente_id)
    origem = f"titular:requisicao:{req.id}"
    relatorio = None

    if dados.acao == "INDEFERIR":
        if not dados.desfecho:
            raise RegraNegocio("Informe o motivo (desfecho) do indeferimento.")
        req.status, desfecho = StatusRequisicao.INDEFERIDA, dados.desfecho
    elif req.tipo == TipoRequisicaoTitular.CONFIRMACAO_TRATAMENTO:
        req.status = StatusRequisicao.RESOLVIDA
        desfecho = "Confirmada a existência de tratamento de dados pessoais para gestão de agenda e encaixes."
    elif req.tipo == TipoRequisicaoTitular.ACESSO:
        relatorio = relatorio_dados(db, paciente)
        req.status = StatusRequisicao.RESOLVIDA
        desfecho = "Relatório de dados pessoais gerado e entregue ao titular."
    elif req.tipo == TipoRequisicaoTitular.CORRECAO:
        if paciente.anonimizado:
            raise RegraNegocio("Paciente anonimizado não pode ser corrigido.")
        cadastros.atualizar_paciente(db, paciente.id, PacienteAtualizar(**req.dados_correcao, ignorar_aviso_duplicidade=True),
                                     usuario, origem=origem, commit=False)
        req.status = StatusRequisicao.RESOLVIDA
        desfecho = f"Dados corrigidos: {', '.join(req.dados_correcao)}."
    else:  # ELIMINACAO
        if _possui_registros_obrigatorios(db, paciente.id):
            # RN18: não elimina; restringe o uso à finalidade legal remanescente
            _revogar(db, paciente, origem, "requisição de eliminação")
            paciente.uso_restrito = True
            paciente.ativo = False
            paciente.data_inativacao = agora()
            for f in db.scalars(select(FilaEspera).where(FilaEspera.paciente_id == paciente.id,
                                                         FilaEspera.ativo.is_(True))).unique():
                f.ativo, f.data_saida, f.motivo_saida = False, agora(), "ELIMINACAO_SOLICITADA"
            req.status = StatusRequisicao.RESOLVIDA_COM_RESTRICAO
            desfecho = ("Há registros de agendamentos, ofertas ou mensagens que precisam ser preservados por "
                        "obrigação legal e para comprovação (RN18). Os dados não foram eliminados: o uso ficou "
                        "restrito a essa finalidade, o contato foi revogado e o paciente saiu da fila de espera.")
        else:
            anonimizar_paciente(db, paciente, origem)
            req.status = StatusRequisicao.RESOLVIDA
            desfecho = "Dados pessoais anonimizados."
    req.desfecho = dados.desfecho or desfecho
    req.data_resolucao = agora()
    req.resolvido_por_id = usuario.id
    auditoria.registrar(db, "REQUISICAO_TITULAR_RESOLVIDA", "requisicao_titular", req.id,
                        auditoria.origem_usuario(usuario), usuario.id, {"tipo": req.tipo.value, "status": req.status.value})
    db.commit()
    saida = {c: getattr(req, c) for c in ("id", "paciente_id", "tipo", "canal", "status", "dados_correcao",
                                          "data_solicitacao", "data_resolucao", "desfecho")}
    saida["dados"] = relatorio
    return saida


def listar_requisicoes(db: Session, params: ParamsPaginacao, status=None, paciente_id=None) -> dict:
    stmt = select(RequisicaoTitular).order_by(RequisicaoTitular.id.desc())
    if status:
        stmt = stmt.where(RequisicaoTitular.status == status)
    if paciente_id:
        stmt = stmt.where(RequisicaoTitular.paciente_id == paciente_id)
    return paginar(db, stmt, params)


# ====================================================================== UC12 – retenção
POLITICAS_PADRAO = {
    CategoriaDado.MENSAGENS: (180, AcaoRetencao.ANONIMIZAR),
    CategoriaDado.RESPOSTAS: (365, AcaoRetencao.ANONIMIZAR),
    CategoriaDado.TENTATIVAS_INVALIDAS: (90, AcaoRetencao.ELIMINAR),
    CategoriaDado.FILA_ESPERA_ENCERRADA: (365, AcaoRetencao.ELIMINAR),
    CategoriaDado.PACIENTES_INATIVOS: (1825, AcaoRetencao.ANONIMIZAR),
}
CONTEUDO_REMOVIDO = "[conteúdo removido pela política de retenção]"


def politicas(db: Session) -> list[PoliticaRetencao]:
    existentes = {p.categoria: p for p in db.scalars(select(PoliticaRetencao))}
    for cat, (prazo, acao) in POLITICAS_PADRAO.items():
        if cat not in existentes:
            p = PoliticaRetencao(categoria=cat, prazo_dias=prazo, acao=acao, ativo=True, versao=1, atualizado_em=agora())
            db.add(p)
            existentes[cat] = p
    db.flush()
    return sorted(existentes.values(), key=lambda p: p.categoria.value)


def atualizar_politicas(db: Session, dados: list[PoliticaAtualizar], usuario) -> list[PoliticaRetencao]:
    atuais = {p.categoria: p for p in politicas(db)}
    for d in dados:
        p = atuais[d.categoria]
        p.prazo_dias, p.ativo = d.prazo_dias, d.ativo
        p.versao += 1
        p.atualizado_em = agora()
        auditoria.registrar(db, "POLITICA_RETENCAO_ALTERADA", "politica_retencao", p.id,
                            auditoria.origem_usuario(usuario), usuario.id,
                            {"categoria": d.categoria.value, "prazo_dias": d.prazo_dias, "versao": p.versao})
    db.commit()
    return list(atuais.values())


def executar_retencao(db: Session, origem: str = "sistema") -> dict[str, dict]:
    """Aplica cada política ativa. Agendamentos, ofertas e logs de auditoria são preservados (RN18, RN19)."""
    resultado: dict[str, dict] = {}
    for p in politicas(db):
        if not p.ativo:
            continue
        limite = agora() - timedelta(days=p.prazo_dias)
        afetados, preservados = 0, 0
        if p.categoria == CategoriaDado.MENSAGENS:
            for m in db.scalars(select(Mensagem).where(Mensagem.data_criacao < limite,
                                                       Mensagem.conteudo != CONTEUDO_REMOVIDO)):
                m.conteudo = CONTEUDO_REMOVIDO
                afetados += 1
        elif p.categoria == CategoriaDado.RESPOSTAS:
            for r in db.scalars(select(RespostaConfirmacao).where(
                RespostaConfirmacao.valida.is_(True), RespostaConfirmacao.data_hora < limite,
                RespostaConfirmacao.resposta_bruta.is_not(None),
            )):
                r.resposta_bruta = None
                r.telefone_origem = mascarar_telefone(r.telefone_origem)
                afetados += 1
        elif p.categoria == CategoriaDado.TENTATIVAS_INVALIDAS:
            afetados = db.execute(delete(RespostaConfirmacao).where(
                RespostaConfirmacao.valida.is_(False), RespostaConfirmacao.data_hora < limite
            )).rowcount or 0
        elif p.categoria == CategoriaDado.FILA_ESPERA_ENCERRADA:
            com_oferta = select(OfertaVaga.fila_id)
            for f in db.scalars(select(FilaEspera).where(FilaEspera.ativo.is_(False),
                                                         FilaEspera.data_saida < limite)).unique():
                if db.scalar(com_oferta.where(OfertaVaga.fila_id == f.id).limit(1)) is not None:
                    preservados += 1  # usado em ofertas: necessário à comprovação
                    continue
                db.delete(f)
                afetados += 1
        elif p.categoria == CategoriaDado.PACIENTES_INATIVOS:
            for pac in db.scalars(select(Paciente).where(Paciente.ativo.is_(False), Paciente.anonimizado.is_(False),
                                                         Paciente.data_inativacao < limite)):
                recente = db.scalar(select(Agendamento.id).where(Agendamento.paciente_id == pac.id,
                                                                 Agendamento.data_hora >= limite).limit(1))
                if recente is not None:
                    preservados += 1
                    continue
                anonimizar_paciente(db, pac, origem)
                afetados += 1
        p.ultima_execucao = agora()
        resultado[p.categoria.value] = {"acao": p.acao.value, "prazo_dias": p.prazo_dias,
                                        "afetados": afetados, "preservados": preservados}
    auditoria.registrar(db, "RETENCAO_EXECUTADA", "politica_retencao", origem=origem, detalhes=resultado)
    db.commit()
    return resultado
