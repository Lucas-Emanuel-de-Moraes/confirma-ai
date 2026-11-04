from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ParametrosEntrada(BaseModel):
    """Valores validados (UC10). Os limites evitam configurações que quebrariam os fluxos."""

    antecedencia_lembrete_horas: int = Field(48, ge=1, le=168, description="Quantas horas antes enviar o lembrete")
    prazo_resposta_min: int = Field(720, ge=5, le=4320, description="Prazo para o paciente responder ao lembrete")
    tentativas_contato: int = Field(3, ge=1, le=10, description="Tentativas de envio antes da falha definitiva")
    janela_reserva_min: int = Field(30, ge=5, le=1440, description="Prazo para aceitar a oferta de encaixe")
    antecedencia_minima_oferta_min: int = Field(
        120, ge=0, le=10080, description="Só reaproveita a vaga se faltar ao menos este tempo para o horário"
    )
    nome_regra: str = Field("Regra padrão", max_length=80)
    considera_prioridade_assistencial: bool = True
    exige_profissional_compativel: bool = False
    criterio_desempate: Literal["DATA_ENTRADA", "ID"] = "DATA_ENTRADA"


class ParametrosSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    unidade_id: int
    versao: int
    vigente: bool
    criado_em: datetime
    criado_por_id: int | None
    antecedencia_lembrete_horas: int
    prazo_resposta_min: int
    tentativas_contato: int
    janela_reserva_min: int
    antecedencia_minima_oferta_min: int
    nome_regra: str
    considera_prioridade_assistencial: bool
    exige_profissional_compativel: bool
    criterio_desempate: str
