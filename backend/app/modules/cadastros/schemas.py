from datetime import datetime, time

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.telefone import normalizar_telefone
from app.modules.cadastros.models import NivelPrioridade, TipoBloqueio


def _tel(v: str | None) -> str | None:
    return normalizar_telefone(v) if v is not None else v


# ---------------------------------------------------------------- Pacientes (HU01)
class PacienteCriar(BaseModel):
    nome: str = Field(min_length=3, max_length=150, examples=["Maria da Silva"])
    telefone: str = Field(description="Telefone/WhatsApp com DDD", examples=["(65) 99999-1234"])
    prioridade_assistencial: NivelPrioridade = NivelPrioridade.NENHUMA
    autorizar_contato: bool = Field(
        default=False, description="Registra a autorização do paciente para contato por mensageria (RF21)"
    )
    ignorar_aviso_duplicidade: bool = Field(
        default=False, description="Confirma o cadastro mesmo se o telefone já pertencer a outro paciente"
    )

    _t = field_validator("telefone")(_tel)

    @field_validator("nome")
    @classmethod
    def _nome(cls, v: str) -> str:
        return " ".join(v.split())


class PacienteAtualizar(BaseModel):
    nome: str | None = Field(default=None, min_length=3, max_length=150)
    telefone: str | None = None
    prioridade_assistencial: NivelPrioridade | None = None
    ignorar_aviso_duplicidade: bool = False

    _t = field_validator("telefone")(_tel)


class PacienteSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    telefone: str | None
    ativo: bool
    prioridade_assistencial: NivelPrioridade
    contato_autorizado: bool
    uso_restrito: bool
    anonimizado: bool
    data_cadastro: datetime


# ---------------------------------------------------------------- Estrutura (UC01)
class Referencia(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str


class EspecialidadeCriar(BaseModel):
    nome: str = Field(min_length=2, max_length=100)


class EspecialidadeAtualizar(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=100)
    ativo: bool | None = None


class EspecialidadeSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    ativo: bool


class UnidadeCriar(BaseModel):
    nome: str = Field(min_length=2, max_length=150)
    endereco: str | None = Field(default=None, max_length=250)
    exige_profissional_especifico: bool = False
    permite_profissional_equivalente: bool = True
    especialidade_ids: list[int] = []


class UnidadeAtualizar(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=150)
    endereco: str | None = None
    exige_profissional_especifico: bool | None = None
    permite_profissional_equivalente: bool | None = None
    especialidade_ids: list[int] | None = None
    ativo: bool | None = None


class UnidadeSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    endereco: str | None
    exige_profissional_especifico: bool
    permite_profissional_equivalente: bool
    ativo: bool
    especialidades: list[Referencia]


class ProfissionalCriar(BaseModel):
    nome: str = Field(min_length=3, max_length=150)
    registro_conselho: str = Field(min_length=3, max_length=40, examples=["CRM-MT 12345"])
    especialidade_ids: list[int] = Field(min_length=1)
    unidade_ids: list[int] = Field(min_length=1)


class ProfissionalAtualizar(BaseModel):
    nome: str | None = Field(default=None, min_length=3, max_length=150)
    registro_conselho: str | None = Field(default=None, min_length=3, max_length=40)
    especialidade_ids: list[int] | None = None
    unidade_ids: list[int] | None = None


class ProfissionalSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    registro_conselho: str
    ativo: bool
    especialidades: list[Referencia]
    unidades: list[Referencia]


class HorarioCriar(BaseModel):
    unidade_id: int
    dia_semana: int = Field(ge=0, le=6, description="0 = segunda-feira ... 6 = domingo")
    hora_inicio: time
    hora_fim: time
    duracao_consulta_min: int = Field(default=30, ge=5, le=240)

    @model_validator(mode="after")
    def _intervalo(self):
        if self.hora_inicio >= self.hora_fim:
            raise ValueError("hora_inicio deve ser anterior a hora_fim.")
        return self


class HorarioSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    profissional_id: int
    unidade_id: int
    dia_semana: int
    hora_inicio: time
    hora_fim: time
    duracao_consulta_min: int
    ativo: bool


class BloqueioCriar(BaseModel):
    unidade_id: int | None = Field(default=None, description="Vazio = todas as unidades")
    profissional_id: int | None = Field(default=None, description="Vazio = todos os profissionais")
    inicio: datetime
    fim: datetime
    tipo: TipoBloqueio = TipoBloqueio.OUTRO
    motivo: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _intervalo(self):
        if self.inicio >= self.fim:
            raise ValueError("inicio deve ser anterior a fim.")
        return self


class BloqueioSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    unidade_id: int | None
    profissional_id: int | None
    inicio: datetime
    fim: datetime
    tipo: TipoBloqueio
    motivo: str | None
