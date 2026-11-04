"""Validação e normalização de telefone/WhatsApp (HU01: formato mínimo do contato)."""

import re


def normalizar_telefone(valor: str) -> str:
    """Devolve o número no formato 55 + DDD + número (somente dígitos).

    Aceita, por exemplo: "(65) 99999-1234", "65999991234", "+55 65 99999-1234".
    """
    digitos = re.sub(r"\D", "", valor or "")
    if len(digitos) in (10, 11):
        digitos = "55" + digitos
    if len(digitos) not in (12, 13) or not digitos.startswith("55"):
        raise ValueError("Telefone inválido: informe DDD e número, por exemplo (65) 99999-1234.")
    ddd = digitos[2:4]
    if ddd[0] == "0":
        raise ValueError("DDD inválido.")
    return digitos


def mascarar_telefone(valor: str | None) -> str | None:
    """Usado em logs e auditoria para não gravar o número completo (RNF07)."""
    if not valor:
        return valor
    return valor[:4] + "*" * max(len(valor) - 8, 0) + valor[-4:]
