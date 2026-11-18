from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.telefone import normalizar_telefone
from app.modules.lgpd.models import (
    AcaoConsentimento,
    AcaoRetencao,
    CategoriaDado,
    StatusRequisicao,
    TipoRequisicaoTitular,
)


class AutorizacaoEntrada(BaseModel):
    origem: str = Field(default="recepcao", max_length=60,
                        description="Como a autorização foi obtida (ex.: recepcao, formulario, telefone)")
    preferencias: dict | None = Field(default=None, examples=[{"periodo_contato": "manha"}])


class PreferenciasContato(BaseModel):
    preferencias: dict = Field(examples=[{"periodo_contato": "tarde", "receber_ofertas_encaixe": True}])


class HistoricoConsentimentoSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    contato_id: int
    acao: AcaoConsentimento
    data_hora: datetime
    origem: str
    detalhes: dict | None


class ConsentimentoSaida(BaseModel):
    paciente_id: int
    autorizado: bool
    data_autorizacao: datetime | None
    data_revogacao: datetime | None
    origem_alteracao: str | None
    preferencias: dict | None
    historico: list[HistoricoConsentimentoSaida]


class DadosCorrecao(BaseModel):
    nome: str | None = Field(default=None, min_length=3, max_length=150)
    telefone: str | None = None

    @field_validator("telefone")
    @classmethod
    def _t(cls, v):
        return normalizar_telefone(v) if v is not None else v


class RequisicaoCriar(BaseModel):
    paciente_id: int
    tipo: TipoRequisicaoTitular
    canal: str = Field(default="presencial", max_length=60)
    dados_correcao: DadosCorrecao | None = None

    @model_validator(mode="after")
    def _correcao(self):
        if self.tipo == TipoRequisicaoTitular.CORRECAO and (
            self.dados_correcao is None or not self.dados_correcao.model_dump(exclude_none=True)
        ):
            raise ValueError("Informe dados_correcao para requisições de correção.")
        return self


class RequisicaoResolver(BaseModel):
    acao: Literal["RESOLVER", "INDEFERIR"] = "RESOLVER"
    desfecho: str | None = Field(default=None, max_length=500)


class RequisicaoSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    paciente_id: int
    tipo: TipoRequisicaoTitular
    canal: str
    status: StatusRequisicao
    dados_correcao: dict | None
    data_solicitacao: datetime
    data_resolucao: datetime | None
    desfecho: str | None


class RequisicaoResolvida(RequisicaoSaida):
    dados: dict | None = Field(default=None, description="Relatório de dados pessoais (requisição de ACESSO)")


class PoliticaSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    categoria: CategoriaDado
    prazo_dias: int
    acao: AcaoRetencao
    ativo: bool
    versao: int
    atualizado_em: datetime
    ultima_execucao: datetime | None


class PoliticaAtualizar(BaseModel):
    categoria: CategoriaDado
    prazo_dias: int = Field(ge=1, le=36500)
    ativo: bool = True
