from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.acesso.permissoes import PERFIS_PADRAO


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class PerfilSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    permissoes: list[str]


def _validar_senha(v: str) -> str:
    if len(v) < 8:
        raise ValueError("A senha deve ter ao menos 8 caracteres.")
    if len(v.encode("utf-8")) > 72:
        raise ValueError("A senha deve ter no máximo 72 bytes.")
    if v.isalpha() or v.isdigit():
        raise ValueError("A senha deve combinar letras e números ou símbolos.")
    return v


def _validar_perfis(v: list[str]) -> list[str]:
    v = [p.upper() for p in v]
    invalidos = [p for p in v if p not in PERFIS_PADRAO]
    if invalidos:
        raise ValueError(f"Perfis inválidos: {invalidos}. Use {list(PERFIS_PADRAO)}.")
    if not v:
        raise ValueError("Informe ao menos um perfil.")
    return v


class UsuarioCriar(BaseModel):
    nome: str = Field(min_length=3, max_length=120)
    login: str = Field(min_length=3, max_length=60, pattern=r"^[a-zA-Z0-9._-]+$")
    senha: str
    perfis: list[str]
    unidade_id: int | None = None

    _senha = field_validator("senha")(_validar_senha)
    _perfis = field_validator("perfis")(_validar_perfis)


class UsuarioAtualizar(BaseModel):
    nome: str | None = Field(default=None, min_length=3, max_length=120)
    senha: str | None = None
    perfis: list[str] | None = None
    unidade_id: int | None = None

    @field_validator("senha")
    @classmethod
    def _s(cls, v):
        return _validar_senha(v) if v is not None else v

    @field_validator("perfis")
    @classmethod
    def _p(cls, v):
        return _validar_perfis(v) if v is not None else v


class UsuarioSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    login: str
    ativo: bool
    mfa_habilitado: bool
    unidade_id: int | None
    criado_em: datetime
    nomes_perfis: list[str] = Field(serialization_alias="perfis")
