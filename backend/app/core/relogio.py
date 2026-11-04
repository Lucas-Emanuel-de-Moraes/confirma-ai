"""Fonte única de data/hora da aplicação.

Todas as datas são gravadas sem fuso (naive) no fuso configurado em FUSO_HORARIO, que é o
fuso da unidade. Centralizar o "agora" permite que os testes avancem o relógio para simular
prazos vencidos (expiração de oferta, ausência de resposta etc.).
"""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.config import settings

_deslocamento = timedelta(0)


def agora() -> datetime:
    return datetime.now(ZoneInfo(settings.FUSO_HORARIO)).replace(tzinfo=None, microsecond=0) + _deslocamento


def hoje() -> date:
    return agora().date()


def avancar(**kwargs) -> None:
    """Avança o relógio da aplicação (somente para testes)."""
    global _deslocamento
    _deslocamento += timedelta(**kwargs)


def reiniciar() -> None:
    global _deslocamento
    _deslocamento = timedelta(0)
