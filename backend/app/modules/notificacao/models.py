import enum
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.tipos import enum_col
from app.modules.cadastros.models import Contato


class TipoMensagem(str, enum.Enum):
    LEMBRETE_CONFIRMACAO = "LEMBRETE_CONFIRMACAO"
    OFERTA_ENCAIXE = "OFERTA_ENCAIXE"
    AVISO = "AVISO"


class StatusMensagem(str, enum.Enum):
    PENDENTE = "PENDENTE"  # gravada no outbox, aguardando envio
    ENVIADA = "ENVIADA"
    FALHA = "FALHA"  # falha definitiva após as retentativas
    RESPONDIDA = "RESPONDIDA"  # identificador já utilizado
    EXPIRADA = "EXPIRADA"
    CANCELADA = "CANCELADA"
    BLOQUEADA = "BLOQUEADA"  # não enviada por falta de autorização (RN16)


class Mensagem(Base):
    __tablename__ = "mensagem"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo: Mapped[TipoMensagem] = mapped_column(enum_col(TipoMensagem))
    conteudo: Mapped[str] = mapped_column(Text)
    # Identificador aleatório, de uso único e com validade (RF24, RNF19)
    identificador_unico: Mapped[str | None] = mapped_column(String(64), unique=True)
    status: Mapped[StatusMensagem] = mapped_column(enum_col(StatusMensagem), default=StatusMensagem.PENDENTE)
    tentativas: Mapped[int] = mapped_column(Integer, default=0)
    data_criacao: Mapped[datetime] = mapped_column(DateTime)
    data_envio: Mapped[datetime | None] = mapped_column(DateTime)
    data_resposta: Mapped[datetime | None] = mapped_column(DateTime)
    data_expiracao: Mapped[datetime | None] = mapped_column(DateTime)
    id_externo: Mapped[str | None] = mapped_column(String(120), index=True)
    motivo: Mapped[str | None] = mapped_column(String(200))
    paciente_id: Mapped[int] = mapped_column(ForeignKey("paciente.id"), index=True)
    contato_id: Mapped[int] = mapped_column(ForeignKey("contato.id"))
    agendamento_id: Mapped[int | None] = mapped_column(ForeignKey("agendamento.id"), index=True)
    oferta_id: Mapped[int | None] = mapped_column(ForeignKey("oferta_vaga.id"), index=True)

    contato: Mapped[Contato] = relationship(lazy="joined")


class StatusOutbox(str, enum.Enum):
    PENDENTE = "PENDENTE"
    ENVIADO = "ENVIADO"
    FALHA_DEFINITIVA = "FALHA_DEFINITIVA"
    CANCELADO = "CANCELADO"


class OutboxEvento(Base):
    """Fila de eventos de saída (padrão outbox) – RNF11 e RNF12.

    É gravada na mesma transação da regra de negócio; uma tarefa periódica envia ao provedor
    com retentativas espaçadas. A chave de idempotência impede mensagens duplicadas.
    """

    __tablename__ = "outbox_evento"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mensagem_id: Mapped[int] = mapped_column(ForeignKey("mensagem.id"), unique=True)
    chave_idempotencia: Mapped[str] = mapped_column(String(120), unique=True)
    status: Mapped[StatusOutbox] = mapped_column(enum_col(StatusOutbox), default=StatusOutbox.PENDENTE)
    tentativas: Mapped[int] = mapped_column(Integer, default=0)
    max_tentativas: Mapped[int] = mapped_column(Integer, default=3)
    proxima_tentativa: Mapped[datetime] = mapped_column(DateTime)
    ultimo_erro: Mapped[str | None] = mapped_column(String(300))
    criado_em: Mapped[datetime] = mapped_column(DateTime)
    processado_em: Mapped[datetime | None] = mapped_column(DateTime)

    mensagem: Mapped[Mensagem] = relationship(lazy="joined")

    __table_args__ = (Index("ix_outbox_pendentes", "status", "proxima_tentativa"),)
