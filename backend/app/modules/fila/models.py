import enum
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.tipos import enum_col
from app.modules.cadastros.models import Especialidade, NivelPrioridade, Paciente, Profissional


class Periodo(str, enum.Enum):
    MANHA = "MANHA"  # 06:00–11:59
    TARDE = "TARDE"  # 12:00–17:59
    NOITE = "NOITE"  # 18:00–23:59
    QUALQUER = "QUALQUER"


def periodo_do_horario(dt: datetime) -> Periodo:
    if 6 <= dt.hour < 12:
        return Periodo.MANHA
    if 12 <= dt.hour < 18:
        return Periodo.TARDE
    return Periodo.NOITE


class FilaEspera(Base):
    """Entrada de um paciente na fila de espera de uma especialidade (RF09)."""

    __tablename__ = "fila_espera"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    paciente_id: Mapped[int] = mapped_column(ForeignKey("paciente.id"), index=True)
    especialidade_id: Mapped[int] = mapped_column(ForeignKey("especialidade.id"), index=True)
    profissional_id: Mapped[int | None] = mapped_column(ForeignKey("profissional.id"))
    data_entrada: Mapped[datetime] = mapped_column(DateTime)
    # Prioridade assistencial fornecida pela instituição (RN09, seção 8.3)
    prioridade: Mapped[NivelPrioridade] = mapped_column(enum_col(NivelPrioridade), default=NivelPrioridade.NENHUMA)
    disponivel_para_encaixe: Mapped[bool] = mapped_column(Boolean, default=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    observacao: Mapped[str | None] = mapped_column(String(200))
    data_saida: Mapped[datetime | None] = mapped_column(DateTime)
    motivo_saida: Mapped[str | None] = mapped_column(String(80))
    agendamento_origem_id: Mapped[int | None] = mapped_column(ForeignKey("agendamento.id"))

    paciente: Mapped[Paciente] = relationship(lazy="joined")
    especialidade: Mapped[Especialidade] = relationship(lazy="joined")
    profissional: Mapped[Profissional | None] = relationship(lazy="joined")
    preferencias: Mapped[list["PreferenciaEncaixe"]] = relationship(
        back_populates="fila", cascade="all, delete-orphan", lazy="selectin", order_by="PreferenciaEncaixe.id"
    )


class PreferenciaEncaixe(Base):
    """Locais, períodos e data em que o paciente pode comparecer a um encaixe (RF10, HU03)."""

    __tablename__ = "preferencia_encaixe"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fila_id: Mapped[int] = mapped_column(ForeignKey("fila_espera.id", ondelete="CASCADE"), index=True)
    unidade_id: Mapped[int | None] = mapped_column(ForeignKey("unidade_saude.id"))  # None = qualquer unidade
    periodo: Mapped[Periodo] = mapped_column(enum_col(Periodo), default=Periodo.QUALQUER)
    data_desejada: Mapped[date | None] = mapped_column(Date)  # None = qualquer data

    fila: Mapped[FilaEspera] = relationship(back_populates="preferencias")

    def is_compativel(self, unidade_id: int, data_hora: datetime) -> bool:
        if self.unidade_id is not None and self.unidade_id != unidade_id:
            return False
        if self.periodo != Periodo.QUALQUER and self.periodo != periodo_do_horario(data_hora):
            return False
        if self.data_desejada is not None and self.data_desejada != data_hora.date():
            return False
        return True


class StatusRemarcacao(str, enum.Enum):
    PENDENTE = "PENDENTE"
    REMARCADA = "REMARCADA"
    MANTIDA = "MANTIDA"
    CANCELADA = "CANCELADA"


class SolicitacaoRemarcacao(Base):
    """Pedido de remarcação feito pelo paciente; tratado pela recepção (RF08, HU02, RN05)."""

    __tablename__ = "solicitacao_remarcacao"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agendamento_id: Mapped[int] = mapped_column(ForeignKey("agendamento.id"), index=True)
    data_solicitacao: Mapped[datetime] = mapped_column(DateTime)
    origem: Mapped[str] = mapped_column(String(80))
    status: Mapped[StatusRemarcacao] = mapped_column(enum_col(StatusRemarcacao), default=StatusRemarcacao.PENDENTE)
    data_resolucao: Mapped[datetime | None] = mapped_column(DateTime)
    observacao: Mapped[str | None] = mapped_column(String(300))
    novo_agendamento_id: Mapped[int | None] = mapped_column(ForeignKey("agendamento.id"))
    resolvido_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))
