from datetime import date, datetime, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.agenda.models import STATUS_OCUPAM_VAGA, Agendamento, StatusAgendamento
from app.modules.cadastros.models import Paciente
from app.modules.recuperacao.models import StatusVaga, VagaLiberada


def ocupante_do_horario(db: Session, profissional_id: int, data_hora: datetime) -> Agendamento | None:
    return db.scalar(
        select(Agendamento).where(
            Agendamento.profissional_id == profissional_id,
            Agendamento.data_hora == data_hora,
            Agendamento.status.in_(STATUS_OCUPAM_VAGA),
        )
    )


def paciente_ocupado(db: Session, paciente_id: int, data_hora: datetime) -> Agendamento | None:
    return db.scalar(
        select(Agendamento).where(
            Agendamento.paciente_id == paciente_id,
            Agendamento.data_hora == data_hora,
            Agendamento.status.in_(STATUS_OCUPAM_VAGA),
        )
    )


def vaga_em_oferta(db: Session, profissional_id: int, data_hora: datetime) -> VagaLiberada | None:
    return db.scalar(
        select(VagaLiberada).where(
            VagaLiberada.profissional_id == profissional_id,
            VagaLiberada.data_hora == data_hora,
            VagaLiberada.status == StatusVaga.EM_OFERTA,
        )
    )


def listar_stmt(
    unidade_id: int | None = None,
    data: date | None = None,
    inicio: datetime | None = None,
    fim: datetime | None = None,
    especialidade_id: int | None = None,
    profissional_id: int | None = None,
    status: list[StatusAgendamento] | None = None,
    paciente_id: int | None = None,
    busca: str | None = None,
):
    stmt = select(Agendamento).order_by(Agendamento.data_hora, Agendamento.id)
    if unidade_id:
        stmt = stmt.where(Agendamento.unidade_id == unidade_id)
    if data:
        stmt = stmt.where(
            Agendamento.data_hora >= datetime.combine(data, time.min),
            Agendamento.data_hora <= datetime.combine(data, time.max),
        )
    if inicio:
        stmt = stmt.where(Agendamento.data_hora >= inicio)
    if fim:
        stmt = stmt.where(Agendamento.data_hora <= fim)
    if especialidade_id:
        stmt = stmt.where(Agendamento.especialidade_id == especialidade_id)
    if profissional_id:
        stmt = stmt.where(Agendamento.profissional_id == profissional_id)
    if status:
        stmt = stmt.where(Agendamento.status.in_(status))
    if paciente_id:
        stmt = stmt.where(Agendamento.paciente_id == paciente_id)
    if busca:
        stmt = stmt.where(
            Agendamento.numero_agendamento.ilike(f"%{busca}%")
            | Agendamento.paciente.has(Paciente.nome.ilike(f"%{busca}%"))
        )
    return stmt
