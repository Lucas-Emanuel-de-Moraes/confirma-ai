FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY app ./app
RUN pip install --upgrade pip && pip install ".[dev]"

COPY . .

EXPOSE 8000

# Aplica as migrations, garante perfis/admin/dados de demonstração e sobe a API
CMD ["sh", "-c", "alembic upgrade head && python -m app.seed --demo && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
