"""Hash de senha (bcrypt) e token JWT (RNF04, RNF05)."""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings


def hash_senha(senha: str) -> str:
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)).decode("utf-8")


def verificar_senha(senha: str, senha_hash: str) -> bool:
    try:
        return bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("utf-8"))
    except ValueError:
        return False


def criar_token(usuario_id: int, perfis: list[str]) -> tuple[str, int]:
    expira_em = settings.JWT_EXPIRA_MINUTOS * 60
    agora = datetime.now(timezone.utc)
    payload = {
        "sub": str(usuario_id),
        "perfis": perfis,
        "iat": agora,
        "exp": agora + timedelta(seconds=expira_em),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITMO), expira_em


def decodificar_token(token: str) -> dict:
    """Lança jwt.PyJWTError se o token for inválido ou estiver expirado."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITMO])
