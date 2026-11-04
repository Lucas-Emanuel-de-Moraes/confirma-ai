import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.tipos import enum_col
from app.modules.cadastros.models import Paciente


class StatusVaga(str, enum.Enum):
    DISPONIVEL = "DISPONIVEL"
    EM_OFERTA = "EM_OFERTA"  # existe reserva temporária válida (RN02)
    PREENCHIDA = "PREENCHIDA"  # encaixe confirmado
    SEM_ELEGIVEIS = "SEM_ELEGIVEIS"  # tratamento manual ou nova consulta da fila
    ENCERRADA = "ENCERRADA"  # fora da janela de reaproveitamento, bloqueio ou encerrada manualmente


class VagaLiberada(Base):
    """Horário liberado por cancelamento, recusa ou ausência de resposta (RF11).

    Tabela acrescentada ao diagrama para registrar o ciclo de vida da vaga e calcular os
    indicadores de vagas recuperadas e tempo de recuperação (RF19).
    """

    __tablename__ = "vaga_liberada"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agendamento_id: Mapped[int] = mapped_column(ForeignKey("agendamento.id"), unique=True)
    unidade_id: Mapped[int] = mapped_column(ForeignKey("unidade_saude.id"), index=True)
    profissional_id: Mapped[int] = mapped_column(ForeignKey("profissional.id"))
    especialidade_id: Mapped[int] = mapped_column(ForeignKey("especialidade.id"))
    data_hora: Mapped[datetime] = mapped_column(DateTime, index=True)
    status: Mapped[StatusVaga] = mapped_column(enum_col(StatusVaga), default=StatusVaga.DISPONIVEL)
    motivo_liberacao: Mapped[str] = mapped_column(String(40))
    observacao: Mapped[str | None] = mapped_column(String(200))
    data_liberacao: Mapped[datetime] = mapped_column(DateTime)
    data_preenchimento: Mapped[datetime | None] = mapped_column(DateTime)
    agendamento_novo_id: Mapped[int | None] = mapped_column(ForeignKey("agendamento.id"))


class StatusOferta(str, enum.Enum):
    RESERVADA = "RESERVADA"
    ACEITA = "ACEITA"
    RECUSADA = "RECUSADA"
    EXPIRADA = "EXPIRADA"
    CANCELADA = "CANCELADA"
    FALHA_CONTATO = "FALHA_CONTATO"


class OfertaVaga(Base):
    __tablename__ = "oferta_vaga"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vaga_id: Mapped[int] = mapped_column(ForeignKey("vaga_liberada.id"), index=True)
    agendamento_id: Mapped[int] = mapped_column(ForeignKey("agendamento.id"))  # agendamento que liberou a vaga
    paciente_id: Mapped[int] = mapped_column(ForeignKey("paciente.id"), index=True)
    fila_id: Mapped[int] = mapped_column(ForeignKey("fila_espera.id"))
    vaga_data_hora: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[StatusOferta] = mapped_column(enum_col(StatusOferta), default=StatusOferta.RESERVADA)
    prazo_resposta: Mapped[datetime] = mapped_column(DateTime)
    reserva_ativa: Mapped[bool] = mapped_column(Boolean, default=True)
    data_criacao: Mapped[datetime] = mapped_column(DateTime)
    data_envio: Mapped[datetime | None] = mapped_column(DateTime)
    data_resposta: Mapped[datetime | None] = mapped_column(DateTime)
    criterio_selecao: Mapped[str | None] = mapped_column(String(300))  # rastreabilidade (RN09)
    motivo: Mapped[str | None] = mapped_column(String(200))
    agendamento_gerado_id: Mapped[int | None] = mapped_column(ForeignKey("agendamento.id"))

    paciente: Mapped[Paciente] = relationship(lazy="joined")
    vaga: Mapped[VagaLiberada] = relationship(lazy="joined")

    __table_args__ = (
        # Última barreira contra dupla marcação: no máximo uma reserva ativa/aceita por vaga (RN13, RNF03)
        Index(
            "uq_oferta_vaga_reserva_ativa",
            "agendamento_id",
            unique=True,
            postgresql_where=text("status IN ('RESERVADA', 'ACEITA')"),
            sqlite_where=text("status IN ('RESERVADA', 'ACEITA')"),
        ),
        Index("ix_oferta_vaga_status_prazo", "status", "prazo_resposta"),
    )
