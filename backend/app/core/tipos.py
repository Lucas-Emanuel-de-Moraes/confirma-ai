from sqlalchemy import Enum


def enum_col(tipo):
    """Enum gravado como texto (VARCHAR), portátil entre PostgreSQL e SQLite."""
    return Enum(tipo, native_enum=False, length=30, validate_strings=True)
