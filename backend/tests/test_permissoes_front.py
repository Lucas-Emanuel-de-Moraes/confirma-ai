"""O front-end mantém uma cópia das permissões (frontend/src/lib/permissoes.ts) só para esconder telas.

Este teste falha se as duas listas deixarem de bater, para ninguém alterar uma e esquecer a outra.
"""
import re
from pathlib import Path

import pytest

from app.modules.acesso import permissoes as P

ARQUIVO_FRONT = Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "permissoes.ts"


def _ler_front() -> tuple[dict[str, str], dict[str, set[str]]]:
    texto = ARQUIVO_FRONT.read_text(encoding="utf-8")
    constantes = dict(re.findall(r"^\s+(\w+): \"([a-z]+:[a-z]+)\",", texto, re.M))
    bloco = texto.split("PERFIS_PADRAO", 1)[1]
    perfis: dict[str, set[str]] = {}
    for nome, corpo in re.findall(r"(\w+): \[(.*?)\]", bloco, re.S):
        perfis[nome] = {constantes[c] for c in re.findall(r"P\.(\w+)", corpo)}
        if '"*"' in corpo:
            perfis[nome].add("*")
    return constantes, perfis


@pytest.mark.skipif(not ARQUIVO_FRONT.exists(), reason="pasta frontend ausente")
def test_permissoes_do_front_iguais_as_do_back():
    constantes, perfis_front = _ler_front()
    valores_back = {v for k, v in vars(P).items() if k.isupper() and isinstance(v, str) and ":" in v}
    assert set(constantes.values()) == valores_back
    assert perfis_front == {perfil: set(lista) for perfil, lista in P.PERFIS_PADRAO.items()}
