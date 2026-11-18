from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.recuperacao.models import StatusOferta, StatusVaga


class VagaSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    agendamento_id: int
    unidade_id: int
    profissional_id: int
    especialidade_id: int
    data_hora: datetime
    status: StatusVaga
    motivo_liberacao: str
    observacao: str | None
    data_liberacao: datetime
    data_preenchimento: datetime | None
    agendamento_novo_id: int | None


class PacienteResumo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str


class OfertaSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    vaga_id: int
    paciente: PacienteResumo
    vaga_data_hora: datetime
    status: StatusOferta
    prazo_resposta: datetime
    reserva_ativa: bool
    data_criacao: datetime
    data_envio: datetime | None
    data_resposta: datetime | None
    criterio_selecao: str | None
    motivo: str | None
    agendamento_gerado_id: int | None


class CancelarOferta(BaseModel):
    motivo: str = Field(min_length=3, max_length=200, examples=["Paciente informou por telefone que não pode"])
    reofertar: bool = Field(default=True, description="Oferecer automaticamente ao próximo da fila")
