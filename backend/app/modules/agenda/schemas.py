from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.modules.agenda.models import StatusAgendamento, TipoComparecimento
from app.modules.cadastros.schemas import Referencia

DESCRICAO_STATUS = {
    StatusAgendamento.AGENDADO: "Agendado – lembrete ainda não enviado",
    StatusAgendamento.AGUARDANDO_RESPOSTA: "Aguardando resposta do paciente",
    StatusAgendamento.CONFIRMADO: "Confirmado pelo paciente",
    StatusAgendamento.NAO_CONFIRMADO: "Não confirmado – vaga liberada",
    StatusAgendamento.CANCELADO: "Cancelado – vaga liberada",
    StatusAgendamento.REMARCACAO_SOLICITADA: "Remarcação solicitada – pendente na recepção",
    StatusAgendamento.SEM_RESPOSTA: "Sem resposta no prazo – vaga liberada",
    StatusAgendamento.REALIZADO: "Atendimento realizado",
    StatusAgendamento.FALTA: "Paciente faltou",
}


class AgendamentoCriar(BaseModel):
    paciente_id: int
    unidade_id: int
    especialidade_id: int
    profissional_id: int
    data_hora: datetime = Field(examples=["2026-11-10T09:00:00"])
    numero_agendamento: str | None = Field(
        default=None, max_length=40, description="Se vazio, o sistema gera um número único"
    )


class PacienteResumo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str


class AgendamentoSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    numero_agendamento: str
    data_hora: datetime
    status: StatusAgendamento
    origem: str
    versao: int
    data_criacao: datetime
    paciente: PacienteResumo
    unidade: Referencia
    especialidade: Referencia
    profissional: Referencia

    @computed_field  # status textual, não apenas por cor (RNF10)
    @property
    def status_descricao(self) -> str:
        return DESCRICAO_STATUS[self.status]


class CancelamentoEntrada(BaseModel):
    motivo: str = Field(min_length=3, max_length=200, examples=["Paciente ligou e cancelou"])


class ComparecimentoEntrada(BaseModel):
    tipo: TipoComparecimento
    observacao: str | None = Field(default=None, max_length=300)


class EventoHistorico(BaseModel):
    data_hora: datetime
    tipo: str
    descricao: str
    origem: str | None = None
