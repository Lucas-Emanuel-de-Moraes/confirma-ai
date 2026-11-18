from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.cadastros.models import Paciente
from app.modules.fila.models import FilaEspera, SolicitacaoRemarcacao, StatusRemarcacao


def entrada_ativa(db: Session, paciente_id: int, especialidade_id: int) -> FilaEspera | None:
    return db.scalar(
        select(FilaEspera).where(
            FilaEspera.paciente_id == paciente_id,
            FilaEspera.especialidade_id == especialidade_id,
            FilaEspera.ativo.is_(True),
        )
    )


def listar_stmt(especialidade_id=None, unidade_id=None, ativo=True, disponivel=None, paciente_id=None, busca=None):
    from app.modules.fila.models import PreferenciaEncaixe

    stmt = select(FilaEspera).order_by(FilaEspera.data_entrada, FilaEspera.id)
    if especialidade_id:
        stmt = stmt.where(FilaEspera.especialidade_id == especialidade_id)
    if unidade_id:
        stmt = stmt.where(FilaEspera.preferencias.any(
            (PreferenciaEncaixe.unidade_id == unidade_id) | PreferenciaEncaixe.unidade_id.is_(None)
        ))
    if ativo is not None:
        stmt = stmt.where(FilaEspera.ativo == ativo)
    if disponivel is not None:
        stmt = stmt.where(FilaEspera.disponivel_para_encaixe == disponivel)
    if paciente_id:
        stmt = stmt.where(FilaEspera.paciente_id == paciente_id)
    if busca:
        stmt = stmt.where(FilaEspera.paciente.has(Paciente.nome.ilike(f"%{busca}%")))
    return stmt


def remarcacoes_stmt(status: StatusRemarcacao | None):
    stmt = select(SolicitacaoRemarcacao).order_by(SolicitacaoRemarcacao.data_solicitacao)
    if status:
        stmt = stmt.where(SolicitacaoRemarcacao.status == status)
    return stmt


def remarcacao_pendente_do_agendamento(db: Session, agendamento_id: int) -> SolicitacaoRemarcacao | None:
    return db.scalar(
        select(SolicitacaoRemarcacao).where(
            SolicitacaoRemarcacao.agendamento_id == agendamento_id,
            SolicitacaoRemarcacao.status == StatusRemarcacao.PENDENTE,
        )
    )
