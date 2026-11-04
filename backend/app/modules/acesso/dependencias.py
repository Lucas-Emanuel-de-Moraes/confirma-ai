"""Dependências do FastAPI para autenticação (JWT) e autorização por perfil (RNF04)."""

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.erros import NaoAutorizado, Proibido
from app.core.seguranca import decodificar_token
from app.modules.acesso.models import Usuario

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def usuario_atual(token: str | None = Depends(oauth2), db: Session = Depends(get_db)) -> Usuario:
    if not token:
        raise NaoAutorizado("Autenticação necessária.")
    try:
        payload = decodificar_token(token)
        usuario_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise NaoAutorizado("Token inválido ou expirado.") from exc
    usuario = db.get(Usuario, usuario_id)
    if usuario is None or not usuario.ativo:
        raise NaoAutorizado("Usuário inexistente ou inativo.")
    return usuario


def exigir(permissao: str):
    """Uso: `usuario: Usuario = Depends(exigir(permissoes.AGENDA_LER))` – devolve 403 sem a permissão."""

    def _dep(usuario: Usuario = Depends(usuario_atual)) -> Usuario:
        if not usuario.possui_permissao(permissao):
            raise Proibido(f"Seu perfil não permite esta operação ({permissao}).")
        return usuario

    return _dep


def unidade_permitida(usuario: Usuario, unidade_id: int | None) -> int | None:
    """Restringe a consulta à unidade em que o usuário está lotado (segregação, seção 5.3)."""
    if usuario.unidade_id is None or usuario.eh_admin:
        return unidade_id
    if unidade_id is not None and unidade_id != usuario.unidade_id:
        raise Proibido("Você só pode consultar dados da sua unidade.")
    return usuario.unidade_id
