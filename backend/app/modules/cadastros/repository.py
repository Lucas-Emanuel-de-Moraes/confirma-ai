from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.modules.cadastros.models import (
    BloqueioAgenda,
    Contato,
    Especialidade,
    HorarioAtendimento,
    Paciente,
    Profissional,
    UnidadeSaude,
)


def pacientes_com_telefone(db: Session, telefone: str, exceto_id: int | None = None) -> list[Paciente]:
    stmt = (
        select(Paciente)
        .join(Contato)
        .where(Contato.valor == telefone, Paciente.ativo.is_(True), Paciente.anonimizado.is_(False))
    )
    if exceto_id:
        stmt = stmt.where(Paciente.id != exceto_id)
    return list(db.scalars(stmt).unique())


def contato_por_telefone(db: Session, telefone: str) -> list[Contato]:
    return list(db.scalars(select(Contato).where(Contato.valor == telefone)))


def listar_pacientes_stmt(busca: str | None, telefone: str | None, ativo: bool | None):
    stmt = select(Paciente).order_by(Paciente.nome, Paciente.id)
    if busca:
        stmt = stmt.where(Paciente.nome.ilike(f"%{busca}%"))
    if telefone:
        stmt = stmt.where(Paciente.contatos.any(Contato.valor.contains(telefone)))
    if ativo is not None:
        stmt = stmt.where(Paciente.ativo == ativo)
    return stmt


def por_ids(db: Session, modelo, ids: list[int]) -> list:
    if not ids:
        return []
    return list(db.scalars(select(modelo).where(modelo.id.in_(ids))))


def nome_existe(db: Session, modelo, nome: str, exceto_id: int | None = None) -> bool:
    stmt = select(modelo.id).where(modelo.nome.ilike(nome))
    if exceto_id:
        stmt = stmt.where(modelo.id != exceto_id)
    return db.scalar(stmt) is not None


def profissional_por_registro(db: Session, registro: str) -> Profissional | None:
    return db.scalar(select(Profissional).where(Profissional.registro_conselho.ilike(registro)))


def horarios_do_profissional(db: Session, profissional_id: int, apenas_ativos: bool = True) -> list[HorarioAtendimento]:
    stmt = select(HorarioAtendimento).where(HorarioAtendimento.profissional_id == profissional_id)
    if apenas_ativos:
        stmt = stmt.where(HorarioAtendimento.ativo.is_(True))
    return list(db.scalars(stmt.order_by(HorarioAtendimento.dia_semana, HorarioAtendimento.hora_inicio)))


def horario_que_atende(db: Session, profissional_id: int, unidade_id: int, data_hora: datetime):
    t = data_hora.time()
    return db.scalar(
        select(HorarioAtendimento).where(
            HorarioAtendimento.profissional_id == profissional_id,
            HorarioAtendimento.unidade_id == unidade_id,
            HorarioAtendimento.dia_semana == data_hora.weekday(),
            HorarioAtendimento.ativo.is_(True),
            HorarioAtendimento.hora_inicio <= t,
            HorarioAtendimento.hora_fim > t,
        )
    )


def bloqueio_vigente(db: Session, unidade_id: int, profissional_id: int, data_hora: datetime):
    """Bloqueio que atinge a unidade e/ou o profissional naquele horário (RN14)."""
    return db.scalar(
        select(BloqueioAgenda)
        .where(
            BloqueioAgenda.inicio <= data_hora,
            BloqueioAgenda.fim > data_hora,
            or_(BloqueioAgenda.unidade_id.is_(None), BloqueioAgenda.unidade_id == unidade_id),
            or_(BloqueioAgenda.profissional_id.is_(None), BloqueioAgenda.profissional_id == profissional_id),
        )
        .limit(1)
    )


def listar_bloqueios_stmt(unidade_id, profissional_id, inicio, fim):
    stmt = select(BloqueioAgenda).order_by(BloqueioAgenda.inicio)
    if unidade_id:
        stmt = stmt.where(or_(BloqueioAgenda.unidade_id.is_(None), BloqueioAgenda.unidade_id == unidade_id))
    if profissional_id:
        stmt = stmt.where(
            or_(BloqueioAgenda.profissional_id.is_(None), BloqueioAgenda.profissional_id == profissional_id)
        )
    if inicio:
        stmt = stmt.where(BloqueioAgenda.fim > inicio)
    if fim:
        stmt = stmt.where(BloqueioAgenda.inicio < fim)
    return stmt


def listar_stmt(modelo, ativo: bool | None, busca: str | None):
    stmt = select(modelo).order_by(modelo.nome)
    if ativo is not None:
        stmt = stmt.where(modelo.ativo == ativo)
    if busca:
        stmt = stmt.where(modelo.nome.ilike(f"%{busca}%"))
    return stmt


def listar_profissionais_stmt(ativo, busca, especialidade_id, unidade_id):
    stmt = listar_stmt(Profissional, ativo, busca)
    if especialidade_id:
        stmt = stmt.where(Profissional.especialidades.any(Especialidade.id == especialidade_id))
    if unidade_id:
        stmt = stmt.where(Profissional.unidades.any(UnidadeSaude.id == unidade_id))
    return stmt

