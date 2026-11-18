import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.tipos import enum_col


class TipoResposta(str, enum.Enum):
    SIM = "SIM"
    NAO = "NAO"
    REMARCAR = "REMARCAR"
    ACEITAR = "ACEITAR"
    RECUSAR = "RECUSAR"
    SAIR = "SAIR"  # revogação da autorização pelo próprio paciente
    INVALIDA = "INVALIDA"


class RespostaConfirmacao(Base):
    """Toda resposta recebida, válida ou não (RN20: tentativas inválidas também ficam registradas)."""

    __tablename__ = "resposta_confirmacao"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo: Mapped[TipoResposta] = mapped_column(enum_col(TipoResposta))
    resposta_bruta: Mapped[str | None] = mapped_column(String(200))
    identificador_recebido: Mapped[str | None] = mapped_column(String(64), index=True)
    telefone_origem: Mapped[str | None] = mapped_column(String(60))
    valida: Mapped[bool] = mapped_column(Boolean)
    motivo_invalidade: Mapped[str | None] = mapped_column(String(60))
    data_hora: Mapped[datetime] = mapped_column(DateTime, index=True)
    origem: Mapped[str] = mapped_column(String(60))
    mensagem_id: Mapped[int | None] = mapped_column(ForeignKey("mensagem.id"), index=True)
    agendamento_id: Mapped[int | None] = mapped_column(ForeignKey("agendamento.id"), index=True)
    oferta_id: Mapped[int | None] = mapped_column(ForeignKey("oferta_vaga.id"))
