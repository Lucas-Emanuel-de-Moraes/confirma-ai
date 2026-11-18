from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ParametroOperacional(Base):
    """Parâmetros versionados por unidade (RF20, UC10). Só uma versão vigente por unidade."""

    __tablename__ = "parametro_operacional"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    unidade_id: Mapped[int] = mapped_column(ForeignKey("unidade_saude.id"), index=True)
    versao: Mapped[int] = mapped_column(Integer)
    vigente: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime)
    criado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))

    antecedencia_lembrete_horas: Mapped[int] = mapped_column(Integer, default=48)
    prazo_resposta_min: Mapped[int] = mapped_column(Integer, default=720)
    tentativas_contato: Mapped[int] = mapped_column(Integer, default=3)
    janela_reserva_min: Mapped[int] = mapped_column(Integer, default=30)
    # Antecedência mínima entre a liberação e o horário da vaga para tentar o reaproveitamento (RF11)
    antecedencia_minima_oferta_min: Mapped[int] = mapped_column(Integer, default=120)

    __table_args__ = (UniqueConstraint("unidade_id", "versao", name="uq_parametro_unidade_versao"),)


class RegraElegibilidade(Base):
    """Critérios de seleção e priorização da fila (RF12, RF13, RN07–RN10), versionados com os parâmetros."""

    __tablename__ = "regra_elegibilidade"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    unidade_id: Mapped[int] = mapped_column(ForeignKey("unidade_saude.id"), index=True)
    versao: Mapped[int] = mapped_column(Integer)
    vigente: Mapped[bool] = mapped_column(Boolean, default=True)
    nome: Mapped[str] = mapped_column(String(80), default="Regra padrão")
    considera_prioridade_assistencial: Mapped[bool] = mapped_column(Boolean, default=True)
    exige_profissional_compativel: Mapped[bool] = mapped_column(Boolean, default=False)
    criterio_desempate: Mapped[str] = mapped_column(String(30), default="DATA_ENTRADA")

    __table_args__ = (UniqueConstraint("unidade_id", "versao", name="uq_regra_unidade_versao"),)
