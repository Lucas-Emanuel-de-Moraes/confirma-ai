from datetime import datetime

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.paginacao import Pagina, ParamsPaginacao, params_paginacao
from app.modules.acesso import permissoes as P
from app.modules.acesso.dependencias import exigir
from app.modules.acesso.models import Usuario
from app.modules.cadastros import service
from app.modules.cadastros.schemas import (
    BloqueioCriar,
    BloqueioSaida,
    EspecialidadeAtualizar,
    EspecialidadeCriar,
    EspecialidadeSaida,
    HorarioCriar,
    HorarioSaida,
    PacienteAtualizar,
    PacienteCriar,
    PacienteSaida,
    ProfissionalAtualizar,
    ProfissionalCriar,
    ProfissionalSaida,
    UnidadeAtualizar,
    UnidadeCriar,
    UnidadeSaida,
)

router_pacientes = APIRouter(prefix="/pacientes", tags=["Pacientes"])
router_estrutura = APIRouter(tags=["Unidades, especialidades e profissionais"])

ler_pac = exigir(P.PACIENTES_LER)
esc_pac = exigir(P.PACIENTES_ESCREVER)
ler_est = exigir(P.ESTRUTURA_LER)
esc_est = exigir(P.ESTRUTURA_ESCREVER)


# ------------------------------------------------------------------ Pacientes
@router_pacientes.get("", response_model=Pagina[PacienteSaida], summary="Lista e busca pacientes")
def listar_pacientes(
    busca: str | None = None, telefone: str | None = None, ativo: bool | None = None,
    params: ParamsPaginacao = Depends(params_paginacao), db: Session = Depends(get_db), _: Usuario = Depends(ler_pac),
):
    return service.listar_pacientes(db, params, busca, telefone, ativo)


@router_pacientes.post("", response_model=PacienteSaida, status_code=201, summary="Cadastra paciente (HU01)")
def criar_paciente(dados: PacienteCriar, db: Session = Depends(get_db), u: Usuario = Depends(esc_pac)):
    return service.criar_paciente(db, dados, u)


@router_pacientes.get("/{paciente_id}", response_model=PacienteSaida)
def obter_paciente(paciente_id: int, db: Session = Depends(get_db), _: Usuario = Depends(ler_pac)):
    return service.obter_paciente(db, paciente_id)


@router_pacientes.put("/{paciente_id}", response_model=PacienteSaida)
def atualizar_paciente(paciente_id: int, dados: PacienteAtualizar, db: Session = Depends(get_db),
                       u: Usuario = Depends(esc_pac)):
    return service.atualizar_paciente(db, paciente_id, dados, u)


@router_pacientes.patch("/{paciente_id}/inativar", response_model=PacienteSaida)
def inativar_paciente(paciente_id: int, db: Session = Depends(get_db), u: Usuario = Depends(esc_pac)):
    return service.inativar_paciente(db, paciente_id, u)


@router_pacientes.patch("/{paciente_id}/reativar", response_model=PacienteSaida)
def reativar_paciente(paciente_id: int, db: Session = Depends(get_db), u: Usuario = Depends(esc_pac)):
    return service.reativar_paciente(db, paciente_id, u)


# ------------------------------------------------------------------ Especialidades
@router_estrutura.get("/especialidades", response_model=Pagina[EspecialidadeSaida])
def listar_especialidades(ativo: bool | None = None, busca: str | None = None,
                          params: ParamsPaginacao = Depends(params_paginacao), db: Session = Depends(get_db),
                          _: Usuario = Depends(ler_est)):
    return service.listar_especialidades(db, params, ativo, busca)


@router_estrutura.post("/especialidades", response_model=EspecialidadeSaida, status_code=201)
def criar_especialidade(dados: EspecialidadeCriar, db: Session = Depends(get_db), u: Usuario = Depends(esc_est)):
    return service.criar_especialidade(db, dados, u)


@router_estrutura.put("/especialidades/{esp_id}", response_model=EspecialidadeSaida)
def atualizar_especialidade(esp_id: int, dados: EspecialidadeAtualizar, db: Session = Depends(get_db),
                            u: Usuario = Depends(esc_est)):
    return service.atualizar_especialidade(db, esp_id, dados, u)


# ------------------------------------------------------------------ Unidades
@router_estrutura.get("/unidades", response_model=Pagina[UnidadeSaida])
def listar_unidades(ativo: bool | None = None, busca: str | None = None,
                    params: ParamsPaginacao = Depends(params_paginacao), db: Session = Depends(get_db),
                    _: Usuario = Depends(ler_est)):
    return service.listar_unidades(db, params, ativo, busca)


@router_estrutura.post("/unidades", response_model=UnidadeSaida, status_code=201)
def criar_unidade(dados: UnidadeCriar, db: Session = Depends(get_db), u: Usuario = Depends(esc_est)):
    return service.criar_unidade(db, dados, u)


@router_estrutura.get("/unidades/{unidade_id}", response_model=UnidadeSaida)
def obter_unidade(unidade_id: int, db: Session = Depends(get_db), _: Usuario = Depends(ler_est)):
    return service.obter_unidade(db, unidade_id)


@router_estrutura.put("/unidades/{unidade_id}", response_model=UnidadeSaida)
def atualizar_unidade(unidade_id: int, dados: UnidadeAtualizar, db: Session = Depends(get_db),
                      u: Usuario = Depends(esc_est)):
    return service.atualizar_unidade(db, unidade_id, dados, u)


# ------------------------------------------------------------------ Profissionais e horários
@router_estrutura.get("/profissionais", response_model=Pagina[ProfissionalSaida])
def listar_profissionais(ativo: bool | None = None, busca: str | None = None, especialidade_id: int | None = None,
                         unidade_id: int | None = None, params: ParamsPaginacao = Depends(params_paginacao),
                         db: Session = Depends(get_db), _: Usuario = Depends(ler_est)):
    return service.listar_profissionais(db, params, ativo, busca, especialidade_id, unidade_id)


@router_estrutura.post("/profissionais", response_model=ProfissionalSaida, status_code=201)
def criar_profissional(dados: ProfissionalCriar, db: Session = Depends(get_db), u: Usuario = Depends(esc_est)):
    return service.criar_profissional(db, dados, u)


@router_estrutura.get("/profissionais/{prof_id}", response_model=ProfissionalSaida)
def obter_profissional(prof_id: int, db: Session = Depends(get_db), _: Usuario = Depends(ler_est)):
    return service.obter_profissional(db, prof_id)


@router_estrutura.put("/profissionais/{prof_id}", response_model=ProfissionalSaida)
def atualizar_profissional(prof_id: int, dados: ProfissionalAtualizar, db: Session = Depends(get_db),
                           u: Usuario = Depends(esc_est)):
    return service.atualizar_profissional(db, prof_id, dados, u)


@router_estrutura.patch("/profissionais/{prof_id}/inativar", response_model=ProfissionalSaida)
def inativar_profissional(prof_id: int, db: Session = Depends(get_db), u: Usuario = Depends(esc_est)):
    return service.inativar_profissional(db, prof_id, u)


@router_estrutura.get("/profissionais/{prof_id}/horarios", response_model=list[HorarioSaida])
def listar_horarios(prof_id: int, db: Session = Depends(get_db), _: Usuario = Depends(ler_est)):
    return service.listar_horarios(db, prof_id)


@router_estrutura.post("/profissionais/{prof_id}/horarios", response_model=HorarioSaida, status_code=201)
def criar_horario(prof_id: int, dados: HorarioCriar, db: Session = Depends(get_db), u: Usuario = Depends(esc_est)):
    return service.criar_horario(db, prof_id, dados, u)


@router_estrutura.delete("/horarios/{horario_id}", status_code=204)
def remover_horario(horario_id: int, db: Session = Depends(get_db), u: Usuario = Depends(esc_est)):
    service.remover_horario(db, horario_id, u)
    return Response(status_code=204)


# ------------------------------------------------------------------ Bloqueios (RN14)
@router_estrutura.get("/bloqueios", response_model=Pagina[BloqueioSaida])
def listar_bloqueios(unidade_id: int | None = None, profissional_id: int | None = None,
                     inicio: datetime | None = None, fim: datetime | None = None,
                     params: ParamsPaginacao = Depends(params_paginacao), db: Session = Depends(get_db),
                     _: Usuario = Depends(ler_est)):
    return service.listar_bloqueios(db, params, unidade_id, profissional_id, inicio, fim)


@router_estrutura.post("/bloqueios", response_model=BloqueioSaida, status_code=201)
def criar_bloqueio(dados: BloqueioCriar, db: Session = Depends(get_db), u: Usuario = Depends(esc_est)):
    return service.criar_bloqueio(db, dados, u)


@router_estrutura.delete("/bloqueios/{bloqueio_id}", status_code=204)
def remover_bloqueio(bloqueio_id: int, db: Session = Depends(get_db), u: Usuario = Depends(esc_est)):
    service.remover_bloqueio(db, bloqueio_id, u)
    return Response(status_code=204)
