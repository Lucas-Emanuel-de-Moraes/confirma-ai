import enum
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.tipos import enum_col
from app.modules.cadastros.models import Especialidade, Paciente, Profissional, UnidadeSaude


class StatusAgendamento(str, enum.Enum):
    AGENDADO = "AGENDADO"
    AGUARDANDO_RESPOSTA = "AGUARDANDO_RESPOSTA"
    CONFIRMADO = "CONFIRMADO"
    NAO_CONFIRMADO = "NAO_CONFIRMADO"
    CANCELADO = "CANCELADO"
    REMARCACAO_SOLICITADA = "REMARCACAO_SOLICITADA"
    SEM_RESPOSTA = "SEM_RESPOSTA"
    REALIZADO = "REALIZADO"
    FALTA = "FALTA"


# Status em que o horário continua ocupado pelo paciente
STATUS_OCUPAM_VAGA = (
    StatusAgendamento.AGENDADO,
    StatusAgendamento.AGUARDANDO_RESPOSTA,
    StatusAgendamento.CONFIRMADO,
    StatusAgendamento.REMARCACAO_SOLICITADA,
    StatusAgendamento.REALIZADO,
    StatusAgendamento.FALTA,
)
# Status que tornam a vaga candidata à recuperação (RF11, RN04)
STATUS_LIBERAM_VAGA = (
    StatusAgendamento.NAO_CONFIRMADO,
    StatusAgendamento.CANCELADO,
    StatusAgendamento.SEM_RESPOSTA,
)

_LISTA_OCUPAM = ", ".join(f"'{s.value}'" for s in STATUS_OCUPAM_VAGA)


class Agendamento(Base):
    __tablename__ = "agendamento"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    numero_agendamento: Mapped[str] = mapped_column(String(40), unique=True)
    data_hora: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[StatusAgendamento] = mapped_column(
        enum_col(StatusAgendamento), default=StatusAgendamento.AGENDADO
    )
    data_criacao: Mapped[datetime] = mapped_column(DateTime)
    origem: Mapped[str] = mapped_column(String(40), default="recepcao")
    paciente_id: Mapped[int] = mapped_column(ForeignKey("paciente.id"), index=True)
    profissional_id: Mapped[int] = mapped_column(ForeignKey("profissional.id"))
    especialidade_id: Mapped[int] = mapped_column(ForeignKey("especialidade.id"))
    unidade_id: Mapped[int] = mapped_column(ForeignKey("unidade_saude.id"))
    # Controle otimista de concorrência (RF17, RNF03)
    versao: Mapped[int] = mapped_column(Integer, nullable=False)

    paciente: Mapped[Paciente] = relationship(lazy="joined")
    profissional: Mapped[Profissional] = relationship(lazy="joined")
    especialidade: Mapped[Especialidade] = relationship(lazy="joined")
    unidade: Mapped[UnidadeSaude] = relationship(lazy="joined")

    __mapper_args__ = {"version_id_col": versao}
    __table_args__ = (
        # Um profissional não pode ter dois agendamentos ativos no mesmo horário (RF17).
        # O índice é parcial para que a vaga liberada (cancelada) possa ser reaproveitada.
        Index(
            "uq_agendamento_profissional_horario_ativo",
            "profissional_id",
            "data_hora",
            unique=True,
            postgresql_where=text(f"status IN ({_LISTA_OCUPAM})"),
            sqlite_where=text(f"status IN ({_LISTA_OCUPAM})"),
        ),
        Index("ix_agendamento_agenda", "unidade_id", "data_hora", "status"),
    )

    @property
    def ocupa_vaga(self) -> bool:
        return self.status in STATUS_OCUPAM_VAGA


class HistoricoStatusAgendamento(Base):
    """Linha do tempo das transições de status (RF07, RN12)."""

    __tablename__ = "historico_status_agendamento"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agendamento_id: Mapped[int] = mapped_column(ForeignKey("agendamento.id"), index=True)
    status_anterior: Mapped[StatusAgendamento | None] = mapped_column(enum_col(StatusAgendamento))
    status_novo: Mapped[StatusAgendamento] = mapped_column(enum_col(StatusAgendamento))
    data_hora: Mapped[datetime] = mapped_column(DateTime)
    origem: Mapped[str] = mapped_column(String(80))
    motivo: Mapped[str | None] = mapped_column(String(200))


class TipoComparecimento(str, enum.Enum):
    COMPARECEU = "COMPARECEU"
    FALTOU = "FALTOU"


class HistoricoComparecimento(Base):
    __tablename__ = "historico_comparecimento"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agendamento_id: Mapped[int] = mapped_column(ForeignKey("agendamento.id"), index=True)
    paciente_id: Mapped[int] = mapped_column(ForeignKey("paciente.id"), index=True)
    tipo: Mapped[TipoComparecimento] = mapped_column(enum_col(TipoComparecimento))
    data_hora: Mapped[datetime] = mapped_column(DateTime)
    observacao: Mapped[str | None] = mapped_column(String(300))
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))
