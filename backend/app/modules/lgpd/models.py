import enum
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.tipos import enum_col


class AcaoConsentimento(str, enum.Enum):
    AUTORIZOU = "AUTORIZOU"
    REVOGOU = "REVOGOU"
    PREFERENCIAS = "PREFERENCIAS"


class HistoricoConsentimento(Base):
    """Cada autorização, revogação ou mudança de preferência, com data, hora e origem (RF21, RN17)."""

    __tablename__ = "historico_consentimento"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    paciente_id: Mapped[int] = mapped_column(ForeignKey("paciente.id"), index=True)
    contato_id: Mapped[int] = mapped_column(ForeignKey("contato.id"))
    acao: Mapped[AcaoConsentimento] = mapped_column(enum_col(AcaoConsentimento))
    data_hora: Mapped[datetime] = mapped_column(DateTime)
    origem: Mapped[str] = mapped_column(String(80))
    detalhes: Mapped[dict | None] = mapped_column(JSON)


class TipoRequisicaoTitular(str, enum.Enum):
    CONFIRMACAO_TRATAMENTO = "CONFIRMACAO_TRATAMENTO"
    ACESSO = "ACESSO"
    CORRECAO = "CORRECAO"
    ELIMINACAO = "ELIMINACAO"


class StatusRequisicao(str, enum.Enum):
    ABERTA = "ABERTA"
    RESOLVIDA = "RESOLVIDA"
    RESOLVIDA_COM_RESTRICAO = "RESOLVIDA_COM_RESTRICAO"  # RN18: dado mantido por obrigação legal
    INDEFERIDA = "INDEFERIDA"


class RequisicaoTitular(Base):
    __tablename__ = "requisicao_titular"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    paciente_id: Mapped[int] = mapped_column(ForeignKey("paciente.id"), index=True)
    tipo: Mapped[TipoRequisicaoTitular] = mapped_column(enum_col(TipoRequisicaoTitular))
    canal: Mapped[str] = mapped_column(String(60))
    status: Mapped[StatusRequisicao] = mapped_column(enum_col(StatusRequisicao), default=StatusRequisicao.ABERTA)
    dados_correcao: Mapped[dict | None] = mapped_column(JSON)
    data_solicitacao: Mapped[datetime] = mapped_column(DateTime)
    data_resolucao: Mapped[datetime | None] = mapped_column(DateTime)
    desfecho: Mapped[str | None] = mapped_column(String(500))
    registrado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))
    resolvido_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))


class CategoriaDado(str, enum.Enum):
    MENSAGENS = "MENSAGENS"  # conteúdo das mensagens enviadas
    RESPOSTAS = "RESPOSTAS"  # texto bruto e telefone das respostas válidas
    TENTATIVAS_INVALIDAS = "TENTATIVAS_INVALIDAS"
    FILA_ESPERA_ENCERRADA = "FILA_ESPERA_ENCERRADA"
    PACIENTES_INATIVOS = "PACIENTES_INATIVOS"


class AcaoRetencao(str, enum.Enum):
    ELIMINAR = "ELIMINAR"
    ANONIMIZAR = "ANONIMIZAR"


class PoliticaRetencao(Base):
    """Prazo de retenção por categoria de dado (RF23, RN19). Classe nova citada na seção 11.3."""

    __tablename__ = "politica_retencao"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    categoria: Mapped[CategoriaDado] = mapped_column(enum_col(CategoriaDado), unique=True)
    prazo_dias: Mapped[int] = mapped_column(Integer)
    acao: Mapped[AcaoRetencao] = mapped_column(enum_col(AcaoRetencao))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    versao: Mapped[int] = mapped_column(Integer, default=1)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime)
    ultima_execucao: Mapped[datetime | None] = mapped_column(DateTime)
