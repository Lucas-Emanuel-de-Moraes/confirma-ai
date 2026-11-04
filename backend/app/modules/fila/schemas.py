from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.agenda.schemas import AgendamentoSaida
from app.modules.cadastros.models import NivelPrioridade
from app.modules.cadastros.schemas import Referencia
from app.modules.fila.models import Periodo, StatusRemarcacao


class PreferenciaEntrada(BaseModel):
    unidade_id: int | None = Field(default=None, description="Vazio = aceita qualquer unidade")
    periodo: Periodo = Periodo.QUALQUER
    data_desejada: date | None = Field(default=None, description="Vazio = qualquer data")


class PreferenciaSaida(PreferenciaEntrada):
    model_config = ConfigDict(from_attributes=True)
    id: int


class FilaCriar(BaseModel):
    paciente_id: int
    especialidade_id: int
    profissional_id: int | None = Field(default=None, description="Profissional desejado (opcional)")
    prioridade: NivelPrioridade | None = Field(
        default=None, description="Se vazio, usa a prioridade assistencial do cadastro do paciente"
    )
    disponivel_para_encaixe: bool = True
    observacao: str | None = Field(default=None, max_length=200)
    preferencias: list[PreferenciaEntrada] = []

    @model_validator(mode="after")
    def _prefs(self):
        if self.disponivel_para_encaixe and not self.preferencias:
            raise ValueError("Informe ao menos uma preferência (local/período) para quem está disponível para encaixe.")
        return self


class PreferenciasAtualizar(BaseModel):
    """HU03: o paciente informa se está disponível e em quais locais e períodos."""

    disponivel_para_encaixe: bool
    preferencias: list[PreferenciaEntrada] = []

    @model_validator(mode="after")
    def _prefs(self):
        if self.disponivel_para_encaixe and not self.preferencias:
            raise ValueError("Informe ao menos uma preferência (local/período) para quem está disponível para encaixe.")
        return self


class PacienteResumo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str


class FilaSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    paciente: PacienteResumo
    especialidade: Referencia
    profissional: Referencia | None
    data_entrada: datetime
    prioridade: NivelPrioridade
    disponivel_para_encaixe: bool
    ativo: bool
    observacao: str | None
    data_saida: datetime | None
    motivo_saida: str | None
    preferencias: list[PreferenciaSaida]


class RemarcacaoSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    agendamento_id: int
    data_solicitacao: datetime
    origem: str
    status: StatusRemarcacao
    data_resolucao: datetime | None
    observacao: str | None
    novo_agendamento_id: int | None


class RemarcacaoPendente(RemarcacaoSaida):
    agendamento: AgendamentoSaida


class RemarcacaoResolver(BaseModel):
    acao: Literal["REMARCAR", "MANTER", "CANCELAR"] = Field(
        description="REMARCAR cria novo agendamento; MANTER confirma o original; CANCELAR libera a vaga"
    )
    nova_data_hora: datetime | None = Field(default=None, description="Obrigatório para REMARCAR")
    novo_profissional_id: int | None = Field(default=None, description="Opcional; padrão: mesmo profissional")
    incluir_fila_espera: bool = Field(default=False, description="Em CANCELAR, coloca o paciente na fila (RF08)")
    observacao: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def _data(self):
        if self.acao == "REMARCAR" and self.nova_data_hora is None:
            raise ValueError("nova_data_hora é obrigatória para REMARCAR.")
        return self
