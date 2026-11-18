from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.agenda.models import STATUS_OCUPAM_VAGA, Agendamento
from app.modules.cadastros.models import Paciente
from app.modules.fila.models import FilaEspera
from app.modules.recuperacao.models import OfertaVaga, StatusOferta, StatusVaga, VagaLiberada


def _bloquear(stmt, modelo):
    return stmt.with_for_update(of=modelo).execution_options(populate_existing=True)


def vaga_para_atualizar(db: Session, vaga_id: int) -> VagaLiberada | None:
    return db.scalar(_bloquear(select(VagaLiberada).where(VagaLiberada.id == vaga_id), VagaLiberada))


def oferta_para_atualizar(db: Session, oferta_id: int) -> OfertaVaga | None:
    return db.scalar(_bloquear(select(OfertaVaga).where(OfertaVaga.id == oferta_id), OfertaVaga))


def vaga_do_agendamento(db: Session, agendamento_id: int) -> VagaLiberada | None:
    return db.scalar(select(VagaLiberada).where(VagaLiberada.agendamento_id == agendamento_id))


def vaga_no_horario(db: Session, profissional_id: int, data_hora: datetime) -> VagaLiberada | None:
    return db.scalar(
        select(VagaLiberada)
        .where(VagaLiberada.profissional_id == profissional_id, VagaLiberada.data_hora == data_hora,
               VagaLiberada.status.not_in([StatusVaga.PREENCHIDA, StatusVaga.EM_OFERTA]))
        .order_by(VagaLiberada.id.desc())
        .limit(1)
    )


def candidatos_da_fila(db: Session, vaga: VagaLiberada, paciente_liberou_id: int) -> list[FilaEspera]:
    """Pré-filtro no banco: fila ativa, disponível, mesma especialidade e paciente apto (UC05)."""
    ja_ofertados = select(OfertaVaga.paciente_id).where(OfertaVaga.vaga_id == vaga.id)
    com_reserva = select(OfertaVaga.paciente_id).where(OfertaVaga.status == StatusOferta.RESERVADA)
    ocupados = select(Agendamento.paciente_id).where(
        Agendamento.data_hora == vaga.data_hora, Agendamento.status.in_(STATUS_OCUPAM_VAGA)
    )
    stmt = (
        select(FilaEspera)
        .join(Paciente, Paciente.id == FilaEspera.paciente_id)
        .where(
            FilaEspera.ativo.is_(True),
            FilaEspera.disponivel_para_encaixe.is_(True),
            FilaEspera.especialidade_id == vaga.especialidade_id,
            Paciente.ativo.is_(True),
            Paciente.uso_restrito.is_(False),
            Paciente.anonimizado.is_(False),
            FilaEspera.paciente_id != paciente_liberou_id,
            FilaEspera.paciente_id.not_in(ja_ofertados),
            FilaEspera.paciente_id.not_in(com_reserva),
            FilaEspera.paciente_id.not_in(ocupados),
        )
    )
    return list(db.scalars(stmt).unique())


def ofertas_reservadas_vencidas(db: Session, agora: datetime) -> list[int]:
    return list(db.scalars(
        select(OfertaVaga.id).where(OfertaVaga.status == StatusOferta.RESERVADA, OfertaVaga.prazo_resposta <= agora)
    ))


def ofertas_reservadas_do_paciente(db: Session, paciente_id: int) -> list[int]:
    return list(db.scalars(
        select(OfertaVaga.id).where(OfertaVaga.status == StatusOferta.RESERVADA, OfertaVaga.paciente_id == paciente_id)
    ))


def vagas_a_reavaliar(db: Session, agora: datetime) -> list[int]:
    return list(db.scalars(
        select(VagaLiberada.id).where(
            VagaLiberada.status.in_([StatusVaga.DISPONIVEL, StatusVaga.SEM_ELEGIVEIS]),
            VagaLiberada.data_hora > agora,
        )
    ))


def listar_vagas_stmt(status=None, unidade_id=None, inicio=None, fim=None):
    stmt = select(VagaLiberada).order_by(VagaLiberada.data_hora)
    if status:
        stmt = stmt.where(VagaLiberada.status == status)
    if unidade_id:
        stmt = stmt.where(VagaLiberada.unidade_id == unidade_id)
    if inicio:
        stmt = stmt.where(VagaLiberada.data_hora >= inicio)
    if fim:
        stmt = stmt.where(VagaLiberada.data_hora <= fim)
    return stmt


def listar_ofertas_stmt(status=None, unidade_id=None, paciente_id=None, vaga_id=None):
    stmt = select(OfertaVaga).order_by(OfertaVaga.id.desc())
    if status:
        stmt = stmt.where(OfertaVaga.status == status)
    if unidade_id:
        stmt = stmt.where(OfertaVaga.vaga.has(VagaLiberada.unidade_id == unidade_id))
    if paciente_id:
        stmt = stmt.where(OfertaVaga.paciente_id == paciente_id)
    if vaga_id:
        stmt = stmt.where(OfertaVaga.vaga_id == vaga_id)
    return stmt
