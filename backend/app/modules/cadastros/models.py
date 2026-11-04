import enum
from datetime import datetime, time

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Time,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.tipos import enum_col


class NivelPrioridade(str, enum.Enum):
    NENHUMA = "NENHUMA"
    BAIXA = "BAIXA"
    MEDIA = "MEDIA"
    ALTA = "ALTA"


PESO_PRIORIDADE = {
    NivelPrioridade.NENHUMA: 0,
    NivelPrioridade.BAIXA: 1,
    NivelPrioridade.MEDIA: 2,
    NivelPrioridade.ALTA: 3,
}


class TipoContato(str, enum.Enum):
    WHATSAPP = "WHATSAPP"
    TELEFONE = "TELEFONE"
    EMAIL = "EMAIL"


class TipoBloqueio(str, enum.Enum):
    FERIADO = "FERIADO"
    INDISPONIBILIDADE = "INDISPONIBILIDADE"
    OUTRO = "OUTRO"


_enum = enum_col


profissional_especialidade = Table(
    "profissional_especialidade",
    Base.metadata,
    Column("profissional_id", ForeignKey("profissional.id", ondelete="CASCADE"), primary_key=True),
    Column("especialidade_id", ForeignKey("especialidade.id", ondelete="CASCADE"), primary_key=True),
)

profissional_unidade = Table(
    "profissional_unidade",
    Base.metadata,
    Column("profissional_id", ForeignKey("profissional.id", ondelete="CASCADE"), primary_key=True),
    Column("unidade_id", ForeignKey("unidade_saude.id", ondelete="CASCADE"), primary_key=True),
)

unidade_especialidade = Table(
    "unidade_especialidade",
    Base.metadata,
    Column("unidade_id", ForeignKey("unidade_saude.id", ondelete="CASCADE"), primary_key=True),
    Column("especialidade_id", ForeignKey("especialidade.id", ondelete="CASCADE"), primary_key=True),
)


class Paciente(Base):
    __tablename__ = "paciente"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(150), index=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    prioridade_assistencial: Mapped[NivelPrioridade] = mapped_column(
        _enum(NivelPrioridade), default=NivelPrioridade.NENHUMA
    )
    data_cadastro: Mapped[datetime] = mapped_column(DateTime)
    data_inativacao: Mapped[datetime | None] = mapped_column(DateTime)
    # LGPD: uso restrito à finalidade legal remanescente (RN18) e anonimização (RF23)
    uso_restrito: Mapped[bool] = mapped_column(Boolean, default=False)
    anonimizado: Mapped[bool] = mapped_column(Boolean, default=False)

    contatos: Mapped[list["Contato"]] = relationship(
        back_populates="paciente", cascade="all, delete-orphan", lazy="selectin", order_by="Contato.id"
    )

    @property
    def contato_principal(self) -> "Contato | None":
        for c in self.contatos:
            if c.tipo == TipoContato.WHATSAPP:
                return c
        return self.contatos[0] if self.contatos else None

    @property
    def telefone(self) -> str | None:
        c = self.contato_principal
        return c.valor if c else None

    @property
    def contato_autorizado(self) -> bool:
        c = self.contato_principal
        return bool(c and c.autorizado)

    @property
    def pode_receber_mensagem(self) -> bool:
        return self.ativo and not self.uso_restrito and not self.anonimizado and self.contato_autorizado


class Contato(Base):
    __tablename__ = "contato"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    paciente_id: Mapped[int] = mapped_column(ForeignKey("paciente.id", ondelete="CASCADE"), index=True)
    tipo: Mapped[TipoContato] = mapped_column(_enum(TipoContato), default=TipoContato.WHATSAPP)
    valor: Mapped[str] = mapped_column(String(60), index=True)
    # Autorização de contato por mensageria (RF21, RN16)
    autorizado: Mapped[bool] = mapped_column(Boolean, default=False)
    data_autorizacao: Mapped[datetime | None] = mapped_column(DateTime)
    data_revogacao: Mapped[datetime | None] = mapped_column(DateTime)
    origem_alteracao: Mapped[str | None] = mapped_column(String(80))
    preferencias: Mapped[dict | None] = mapped_column(JSON)

    paciente: Mapped[Paciente] = relationship(back_populates="contatos")


class Especialidade(Base):
    __tablename__ = "especialidade"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), unique=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)


class UnidadeSaude(Base):
    __tablename__ = "unidade_saude"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(150), unique=True)
    endereco: Mapped[str | None] = mapped_column(String(250))
    # RN08: oferta só para o mesmo profissional, ou permite profissional equivalente
    exige_profissional_especifico: Mapped[bool] = mapped_column(Boolean, default=False)
    permite_profissional_equivalente: Mapped[bool] = mapped_column(Boolean, default=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    especialidades: Mapped[list[Especialidade]] = relationship(
        secondary=unidade_especialidade, lazy="selectin", order_by="Especialidade.nome"
    )


class Profissional(Base):
    __tablename__ = "profissional"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(150))
    registro_conselho: Mapped[str] = mapped_column(String(40), unique=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    especialidades: Mapped[list[Especialidade]] = relationship(
        secondary=profissional_especialidade, lazy="selectin", order_by="Especialidade.nome"
    )
    unidades: Mapped[list[UnidadeSaude]] = relationship(
        secondary=profissional_unidade, lazy="selectin", order_by="UnidadeSaude.nome"
    )

    def possui_especialidade(self, especialidade_id: int) -> bool:
        return any(e.id == especialidade_id for e in self.especialidades)

    def atende_na_unidade(self, unidade_id: int) -> bool:
        return any(u.id == unidade_id for u in self.unidades)


class HorarioAtendimento(Base):
    """Horários em que o profissional atende em uma unidade (UC01)."""

    __tablename__ = "horario_atendimento"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profissional_id: Mapped[int] = mapped_column(ForeignKey("profissional.id", ondelete="CASCADE"), index=True)
    unidade_id: Mapped[int] = mapped_column(ForeignKey("unidade_saude.id", ondelete="CASCADE"))
    dia_semana: Mapped[int] = mapped_column(Integer)  # 0 = segunda ... 6 = domingo
    hora_inicio: Mapped[time] = mapped_column(Time)
    hora_fim: Mapped[time] = mapped_column(Time)
    duracao_consulta_min: Mapped[int] = mapped_column(Integer, default=30)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)


class BloqueioAgenda(Base):
    """Feriados, indisponibilidade de profissional e outros bloqueios (RN14)."""

    __tablename__ = "bloqueio_agenda"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    unidade_id: Mapped[int | None] = mapped_column(ForeignKey("unidade_saude.id", ondelete="CASCADE"))
    profissional_id: Mapped[int | None] = mapped_column(ForeignKey("profissional.id", ondelete="CASCADE"))
    inicio: Mapped[datetime] = mapped_column(DateTime)
    fim: Mapped[datetime] = mapped_column(DateTime)
    tipo: Mapped[TipoBloqueio] = mapped_column(_enum(TipoBloqueio), default=TipoBloqueio.OUTRO)
    motivo: Mapped[str | None] = mapped_column(String(200))
