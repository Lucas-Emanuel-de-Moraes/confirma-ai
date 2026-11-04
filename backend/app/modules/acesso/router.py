from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.paginacao import Pagina, ParamsPaginacao, params_paginacao
from app.modules.acesso import permissoes as P
from app.modules.acesso import service
from app.modules.acesso.dependencias import exigir, usuario_atual
from app.modules.acesso.models import Usuario
from app.modules.acesso.schemas import PerfilSaida, Token, UsuarioAtualizar, UsuarioCriar, UsuarioSaida

router_auth = APIRouter(prefix="/auth", tags=["Autenticação"])
router_usuarios = APIRouter(prefix="/usuarios", tags=["Usuários e perfis"])


@router_auth.post("/login", response_model=Token, summary="Autentica e devolve um token JWT")
def login(request: Request, form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Fluxo OAuth2 com senha: envie `username` e `password` como formulário."""
    ip = request.client.host if request.client else None
    token, expira = service.autenticar(db, form.username, form.password, ip)
    return Token(access_token=token, expires_in=expira)


@router_auth.get("/me", response_model=UsuarioSaida, summary="Dados do usuário autenticado")
def me(usuario: Usuario = Depends(usuario_atual)):
    return usuario


@router_usuarios.get("", response_model=Pagina[UsuarioSaida])
def listar(
    ativo: bool | None = None,
    busca: str | None = None,
    params: ParamsPaginacao = Depends(params_paginacao),
    db: Session = Depends(get_db),
    _: Usuario = Depends(exigir(P.USUARIOS)),
):
    return service.listar(db, params, ativo, busca)


@router_usuarios.get("/perfis", response_model=list[PerfilSaida])
def perfis(db: Session = Depends(get_db), _: Usuario = Depends(exigir(P.USUARIOS))):
    return service.listar_perfis(db)


@router_usuarios.post("", response_model=UsuarioSaida, status_code=201)
def criar(dados: UsuarioCriar, db: Session = Depends(get_db), autor: Usuario = Depends(exigir(P.USUARIOS))):
    return service.criar(db, dados, autor)


@router_usuarios.get("/{usuario_id}", response_model=UsuarioSaida)
def obter(usuario_id: int, db: Session = Depends(get_db), _: Usuario = Depends(exigir(P.USUARIOS))):
    return service.obter(db, usuario_id)


@router_usuarios.put("/{usuario_id}", response_model=UsuarioSaida)
def atualizar(
    usuario_id: int, dados: UsuarioAtualizar, db: Session = Depends(get_db),
    autor: Usuario = Depends(exigir(P.USUARIOS)),
):
    return service.atualizar(db, usuario_id, dados, autor)


@router_usuarios.patch("/{usuario_id}/inativar", response_model=UsuarioSaida)
def inativar(usuario_id: int, db: Session = Depends(get_db), autor: Usuario = Depends(exigir(P.USUARIOS))):
    return service.inativar(db, usuario_id, autor)
