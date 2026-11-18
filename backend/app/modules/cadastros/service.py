"""Pacientes, unidades, especialidades, profissionais, horários e bloqueios (RF01, RF02, HU01, UC01)."""

from sqlalchemy.orm import Session

from app.core.erros import Conflito, NaoEncontrado, RegraNegocio
from app.core.paginacao import ParamsPaginacao, paginar
from app.core.relogio import agora
from app.core.telefone import mascarar_telefone
from app.modules.auditoria import service as auditoria
from app.modules.cadastros import repository as repo
from app.modules.cadastros.models import (
    BloqueioAgenda,
    Contato,
    Especialidade,
    HorarioAtendimento,
    Paciente,
    Profissional,
    TipoContato,
    UnidadeSaude,
)
from app.modules.cadastros.schemas import (
    BloqueioCriar,
    EspecialidadeAtualizar,
    EspecialidadeCriar,
    HorarioCriar,
    PacienteAtualizar,
    PacienteCriar,
    ProfissionalAtualizar,
    ProfissionalCriar,
    UnidadeAtualizar,
    UnidadeCriar,
)
from app.modules.lgpd import consentimento
from app.modules.lgpd.models import AcaoConsentimento
from app.modules.parametros import service as parametros


def _obter(db: Session, modelo, id_: int, nome: str):
    obj = db.get(modelo, id_)
    if obj is None:
        raise NaoEncontrado(f"{nome} não encontrado(a).")
    return obj


# ====================================================================== Pacientes
def _avisar_duplicidade(db: Session, telefone: str, ignorar: bool, exceto_id: int | None = None) -> None:
    if ignorar:
        return
    existentes = repo.pacientes_com_telefone(db, telefone, exceto_id)
    if existentes:
        raise Conflito(
            "Já existe paciente ativo com este telefone. Confira o cadastro ou envie "
            "ignorar_aviso_duplicidade=true para cadastrar mesmo assim.",
            codigo="TELEFONE_DUPLICADO",
            campos=[{"campo": "telefone", "erro": f"usado pelo paciente id {existentes[0].id}"}],
        )


def criar_paciente(db: Session, dados: PacienteCriar, usuario) -> Paciente:
    _avisar_duplicidade(db, dados.telefone, dados.ignorar_aviso_duplicidade)
    origem = auditoria.origem_usuario(usuario)
    paciente = Paciente(
        nome=dados.nome,
        prioridade_assistencial=dados.prioridade_assistencial,
        ativo=True,
        data_cadastro=agora(),
    )
    contato = Contato(tipo=TipoContato.WHATSAPP, valor=dados.telefone, autorizado=False)
    paciente.contatos.append(contato)
    db.add(paciente)
    db.flush()
    if dados.autorizar_contato:
        consentimento.autorizar_contato(db, contato, origem)
    auditoria.registrar(
        db, "PACIENTE_CRIADO", "paciente", paciente.id, origem, usuario.id,
        {"telefone": mascarar_telefone(dados.telefone), "autorizou_contato": dados.autorizar_contato},
    )
    db.commit()
    return paciente


def obter_paciente(db: Session, paciente_id: int) -> Paciente:
    return _obter(db, Paciente, paciente_id, "Paciente")


def atualizar_paciente(db: Session, paciente_id: int, dados: PacienteAtualizar, usuario, origem: str | None = None,
                       commit: bool = True) -> Paciente:
    paciente = obter_paciente(db, paciente_id)
    if paciente.anonimizado:
        raise RegraNegocio("Paciente anonimizado não pode ser alterado.")
    origem = origem or auditoria.origem_usuario(usuario)
    campos = []
    if dados.nome is not None and dados.nome != paciente.nome:
        paciente.nome = dados.nome
        campos.append("nome")
    if dados.prioridade_assistencial is not None and dados.prioridade_assistencial != paciente.prioridade_assistencial:
        paciente.prioridade_assistencial = dados.prioridade_assistencial
        campos.append("prioridade_assistencial")
    if dados.telefone is not None:
        contato = paciente.contato_principal
        if contato is None:
            paciente.contatos.append(Contato(tipo=TipoContato.WHATSAPP, valor=dados.telefone))
            campos.append("telefone")
        elif contato.valor != dados.telefone:
            _avisar_duplicidade(db, dados.telefone, dados.ignorar_aviso_duplicidade, paciente.id)
            contato.valor = dados.telefone
            campos.append("telefone")
            # O novo número ainda não autorizou o contato: a autorização precisa ser registrada de novo.
            if contato.autorizado:
                contato.autorizado = False
                contato.data_revogacao = agora()
                contato.origem_alteracao = origem
                consentimento.registrar_historico(
                    db, contato, AcaoConsentimento.REVOGOU, origem, {"motivo": "troca de número"}
                )
    auditoria.registrar(db, "PACIENTE_ALTERADO", "paciente", paciente.id, origem,
                        getattr(usuario, "id", None), {"campos": campos})
    if commit:
        db.commit()
    return paciente


def inativar_paciente(db: Session, paciente_id: int, usuario) -> Paciente:
    """Inativa sem apagar o histórico (HU01)."""
    paciente = obter_paciente(db, paciente_id)
    paciente.ativo = False
    paciente.data_inativacao = agora()
    auditoria.registrar(db, "PACIENTE_INATIVADO", "paciente", paciente.id, auditoria.origem_usuario(usuario), usuario.id)
    db.commit()
    return paciente


def reativar_paciente(db: Session, paciente_id: int, usuario) -> Paciente:
    paciente = obter_paciente(db, paciente_id)
    if paciente.anonimizado:
        raise RegraNegocio("Paciente anonimizado não pode ser reativado.")
    paciente.ativo = True
    paciente.data_inativacao = None
    auditoria.registrar(db, "PACIENTE_REATIVADO", "paciente", paciente.id, auditoria.origem_usuario(usuario), usuario.id)
    db.commit()
    return paciente


def listar_pacientes(db: Session, params: ParamsPaginacao, busca, telefone, ativo) -> dict:
    return paginar(db, repo.listar_pacientes_stmt(busca, telefone, ativo), params)


# ====================================================================== Especialidades
def criar_especialidade(db: Session, dados: EspecialidadeCriar, usuario) -> Especialidade:
    if repo.nome_existe(db, Especialidade, dados.nome):
        raise Conflito("Especialidade já cadastrada.", codigo="REGISTRO_DUPLICADO")
    esp = Especialidade(nome=dados.nome.strip(), ativo=True)
    db.add(esp)
    db.flush()
    auditoria.registrar(db, "ESPECIALIDADE_CRIADA", "especialidade", esp.id, auditoria.origem_usuario(usuario), usuario.id)
    db.commit()
    return esp


def atualizar_especialidade(db: Session, esp_id: int, dados: EspecialidadeAtualizar, usuario) -> Especialidade:
    esp = _obter(db, Especialidade, esp_id, "Especialidade")
    if dados.nome and repo.nome_existe(db, Especialidade, dados.nome, esp.id):
        raise Conflito("Especialidade já cadastrada.", codigo="REGISTRO_DUPLICADO")
    if dados.nome:
        esp.nome = dados.nome.strip()
    if dados.ativo is not None:
        esp.ativo = dados.ativo
    auditoria.registrar(db, "ESPECIALIDADE_ALTERADA", "especialidade", esp.id, auditoria.origem_usuario(usuario),
                        usuario.id, dados.model_dump(exclude_none=True))
    db.commit()
    return esp


def listar_especialidades(db: Session, params: ParamsPaginacao, ativo, busca) -> dict:
    return paginar(db, repo.listar_stmt(Especialidade, ativo, busca), params)


# ====================================================================== Unidades
def _especialidades(db: Session, ids: list[int]) -> list[Especialidade]:
    encontradas = repo.por_ids(db, Especialidade, ids)
    if len(encontradas) != len(set(ids)):
        raise RegraNegocio("Especialidade inexistente na lista informada.",
                           campos=[{"campo": "especialidade_ids", "erro": "inexistente"}])
    return encontradas


def criar_unidade(db: Session, dados: UnidadeCriar, usuario) -> UnidadeSaude:
    if repo.nome_existe(db, UnidadeSaude, dados.nome):
        raise Conflito("Já existe uma unidade com este nome.", codigo="REGISTRO_DUPLICADO")
    unidade = UnidadeSaude(
        nome=dados.nome.strip(), endereco=dados.endereco,
        exige_profissional_especifico=dados.exige_profissional_especifico,
        permite_profissional_equivalente=dados.permite_profissional_equivalente,
        ativo=True, especialidades=_especialidades(db, dados.especialidade_ids),
    )
    db.add(unidade)
    db.flush()
    parametros.vigente(db, unidade.id)  # versão 1 dos parâmetros com valores padrão
    auditoria.registrar(db, "UNIDADE_CRIADA", "unidade_saude", unidade.id, auditoria.origem_usuario(usuario), usuario.id)
    db.commit()
    return unidade


def atualizar_unidade(db: Session, unidade_id: int, dados: UnidadeAtualizar, usuario) -> UnidadeSaude:
    unidade = _obter(db, UnidadeSaude, unidade_id, "Unidade")
    if dados.nome and repo.nome_existe(db, UnidadeSaude, dados.nome, unidade.id):
        raise Conflito("Já existe uma unidade com este nome.", codigo="REGISTRO_DUPLICADO")
    for campo in ("nome", "endereco", "exige_profissional_especifico", "permite_profissional_equivalente", "ativo"):
        valor = getattr(dados, campo)
        if valor is not None:
            setattr(unidade, campo, valor)
    if dados.especialidade_ids is not None:
        unidade.especialidades = _especialidades(db, dados.especialidade_ids)
    auditoria.registrar(db, "UNIDADE_ALTERADA", "unidade_saude", unidade.id, auditoria.origem_usuario(usuario),
                        usuario.id, dados.model_dump(exclude_none=True))
    db.commit()
    return unidade


def obter_unidade(db: Session, unidade_id: int) -> UnidadeSaude:
    return _obter(db, UnidadeSaude, unidade_id, "Unidade")


def listar_unidades(db: Session, params: ParamsPaginacao, ativo, busca) -> dict:
    return paginar(db, repo.listar_stmt(UnidadeSaude, ativo, busca), params)


# ====================================================================== Profissionais
def _unidades(db: Session, ids: list[int]) -> list[UnidadeSaude]:
    encontradas = repo.por_ids(db, UnidadeSaude, ids)
    if len(encontradas) != len(set(ids)):
        raise RegraNegocio("Unidade inexistente na lista informada.", campos=[{"campo": "unidade_ids", "erro": "inexistente"}])
    return encontradas


def criar_profissional(db: Session, dados: ProfissionalCriar, usuario) -> Profissional:
    if repo.profissional_por_registro(db, dados.registro_conselho):
        raise Conflito("Já existe profissional com este registro de conselho.", codigo="REGISTRO_DUPLICADO")
    prof = Profissional(
        nome=dados.nome, registro_conselho=dados.registro_conselho.strip(), ativo=True,
        especialidades=_especialidades(db, dados.especialidade_ids), unidades=_unidades(db, dados.unidade_ids),
    )
    db.add(prof)
    db.flush()
    auditoria.registrar(db, "PROFISSIONAL_CRIADO", "profissional", prof.id, auditoria.origem_usuario(usuario), usuario.id)
    db.commit()
    return prof


def atualizar_profissional(db: Session, prof_id: int, dados: ProfissionalAtualizar, usuario) -> Profissional:
    prof = _obter(db, Profissional, prof_id, "Profissional")
    if dados.registro_conselho:
        outro = repo.profissional_por_registro(db, dados.registro_conselho)
        if outro and outro.id != prof.id:
            raise Conflito("Já existe profissional com este registro de conselho.", codigo="REGISTRO_DUPLICADO")
        prof.registro_conselho = dados.registro_conselho.strip()
    if dados.nome:
        prof.nome = dados.nome
    if dados.especialidade_ids is not None:
        prof.especialidades = _especialidades(db, dados.especialidade_ids)
    if dados.unidade_ids is not None:
        prof.unidades = _unidades(db, dados.unidade_ids)
    auditoria.registrar(db, "PROFISSIONAL_ALTERADO", "profissional", prof.id, auditoria.origem_usuario(usuario),
                        usuario.id, dados.model_dump(exclude_none=True))
    db.commit()
    return prof


def inativar_profissional(db: Session, prof_id: int, usuario) -> Profissional:
    prof = _obter(db, Profissional, prof_id, "Profissional")
    prof.ativo = False
    auditoria.registrar(db, "PROFISSIONAL_INATIVADO", "profissional", prof.id, auditoria.origem_usuario(usuario), usuario.id)
    db.commit()
    return prof


def obter_profissional(db: Session, prof_id: int) -> Profissional:
    return _obter(db, Profissional, prof_id, "Profissional")


def listar_profissionais(db: Session, params, ativo, busca, especialidade_id, unidade_id) -> dict:
    return paginar(db, repo.listar_profissionais_stmt(ativo, busca, especialidade_id, unidade_id), params)


# ====================================================================== Horários e bloqueios
def criar_horario(db: Session, prof_id: int, dados: HorarioCriar, usuario) -> HorarioAtendimento:
    prof = obter_profissional(db, prof_id)
    if not prof.atende_na_unidade(dados.unidade_id):
        raise RegraNegocio("O profissional não está vinculado a esta unidade.",
                           campos=[{"campo": "unidade_id", "erro": "profissional não vinculado"}])
    for h in repo.horarios_do_profissional(db, prof.id):
        if h.dia_semana == dados.dia_semana and h.hora_inicio < dados.hora_fim and dados.hora_inicio < h.hora_fim:
            raise Conflito(
                f"Horário conflita com outro já cadastrado (id {h.id}, {h.hora_inicio}–{h.hora_fim}).",
                codigo="HORARIO_CONFLITANTE",
            )
    horario = HorarioAtendimento(profissional_id=prof.id, ativo=True, **dados.model_dump())
    db.add(horario)
    db.flush()
    auditoria.registrar(db, "HORARIO_CRIADO", "horario_atendimento", horario.id, auditoria.origem_usuario(usuario),
                        usuario.id, {"profissional_id": prof.id, "unidade_id": dados.unidade_id})
    db.commit()
    return horario


def listar_horarios(db: Session, prof_id: int) -> list[HorarioAtendimento]:
    obter_profissional(db, prof_id)
    return repo.horarios_do_profissional(db, prof_id)


def remover_horario(db: Session, horario_id: int, usuario) -> None:
    horario = _obter(db, HorarioAtendimento, horario_id, "Horário")
    horario.ativo = False
    auditoria.registrar(db, "HORARIO_DESATIVADO", "horario_atendimento", horario.id,
                        auditoria.origem_usuario(usuario), usuario.id)
    db.commit()


def criar_bloqueio(db: Session, dados: BloqueioCriar, usuario) -> BloqueioAgenda:
    if dados.unidade_id:
        obter_unidade(db, dados.unidade_id)
    if dados.profissional_id:
        obter_profissional(db, dados.profissional_id)
    bloqueio = BloqueioAgenda(**dados.model_dump())
    db.add(bloqueio)
    db.flush()
    auditoria.registrar(db, "BLOQUEIO_CRIADO", "bloqueio_agenda", bloqueio.id, auditoria.origem_usuario(usuario),
                        usuario.id, {"tipo": dados.tipo.value})
    db.commit()
    return bloqueio


def listar_bloqueios(db: Session, params, unidade_id, profissional_id, inicio, fim) -> dict:
    return paginar(db, repo.listar_bloqueios_stmt(unidade_id, profissional_id, inicio, fim), params)


def remover_bloqueio(db: Session, bloqueio_id: int, usuario) -> None:
    bloqueio = _obter(db, BloqueioAgenda, bloqueio_id, "Bloqueio")
    db.delete(bloqueio)
    auditoria.registrar(db, "BLOQUEIO_REMOVIDO", "bloqueio_agenda", bloqueio_id, auditoria.origem_usuario(usuario), usuario.id)
    db.commit()
