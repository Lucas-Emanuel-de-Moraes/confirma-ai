"""Configuração dos testes.

Por padrão os testes usam SQLite em memória (rápido, sem dependências). Para rodar contra o
PostgreSQL – inclusive os testes de concorrência – defina TEST_DATABASE_URL, por exemplo:

    TEST_DATABASE_URL=postgresql+psycopg://confirma:confirma@localhost:5432/confirma_ai_test pytest
"""

import os
from datetime import datetime, time, timedelta

os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ["AGENDADOR_ATIVO"] = "false"
os.environ["MENSAGERIA_PROVEDOR"] = "simulador"
os.environ["AMBIENTE"] = "teste"
os.environ["BCRYPT_ROUNDS"] = "4"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app import tarefas  # noqa: E402
from app.core import database, relogio  # noqa: E402
from app.core.database import Base  # noqa: E402
from app.main import app  # noqa: E402
from app.modules.notificacao.gateway import obter_gateway  # noqa: E402
from app.seed import seed_basico  # noqa: E402

EH_POSTGRES = database.engine.dialect.name == "postgresql"


@pytest.fixture(scope="session", autouse=True)
def _esquema():
    Base.metadata.drop_all(database.engine)
    Base.metadata.create_all(database.engine)
    yield


@pytest.fixture(autouse=True)
def _limpar():
    with database.engine.begin() as conn:
        if EH_POSTGRES:
            nomes = ", ".join(t.name for t in Base.metadata.sorted_tables)
            conn.execute(text(f"TRUNCATE {nomes} RESTART IDENTITY CASCADE"))
        else:
            for t in reversed(Base.metadata.sorted_tables):
                conn.execute(t.delete())
    with database.SessionLocal() as db:
        seed_basico(db)
    relogio.reiniciar()
    obter_gateway().limpar()
    yield
    relogio.reiniciar()


@pytest.fixture
def client():
    return TestClient(app)


def login(client, usuario="admin", senha="Admin@123") -> dict:
    r = client.post("/api/v1/auth/login", data={"username": usuario, "password": senha})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def admin(client):
    return login(client)


def rodar(nome: str) -> dict:
    return tarefas.executar(nome)


def mensagens_para(telefone: str) -> list[dict]:
    return [m for m in reversed(obter_gateway().caixa_saida) if m["destino"] == telefone]


def ultima_mensagem(telefone: str) -> dict:
    msgs = mensagens_para(telefone)
    assert msgs, f"Nenhuma mensagem enviada para {telefone}"
    return msgs[0]


def responder(client, telefone: str, resposta: str, identificador: str | None = None) -> dict:
    if identificador is None:
        identificador = ultima_mensagem(telefone)["identificador"]
    r = client.post("/api/v1/simulador/responder",
                    json={"telefone": telefone, "identificador": identificador, "resposta": resposta})
    assert r.status_code == 200, r.text
    return r.json()["resultados"][0]


def amanha_as(hora: int, minuto: int = 0, dias: int = 1) -> str:
    d = relogio.agora().date() + timedelta(days=dias)
    return datetime.combine(d, time(hora, minuto)).isoformat()


class Cenario:
    """Unidade, especialidade, profissional com horário amplo e pacientes autorizados – via API."""

    def __init__(self, client, headers):
        self.c, self.h = client, headers
        self.esp = self.post("/especialidades", {"nome": "Cardiologia"})["id"]
        self.unidade = self.post("/unidades", {"nome": "Clínica Teste", "especialidade_ids": [self.esp]})["id"]
        self.prof = self.criar_profissional("Dra. Ana", "CRM 1")
        self.pacientes: dict[str, dict] = {}

    def post(self, rota, corpo, esperado=201):
        r = self.c.post(f"/api/v1{rota}", json=corpo, headers=self.h)
        assert r.status_code == esperado, r.text
        return r.json()

    def criar_profissional(self, nome, registro, unidade=None):
        pid = self.post("/profissionais", {"nome": nome, "registro_conselho": registro,
                                            "especialidade_ids": [self.esp],
                                            "unidade_ids": [unidade or self.unidade]})["id"]
        for dia in range(7):
            self.post(f"/profissionais/{pid}/horarios", {"unidade_id": unidade or self.unidade, "dia_semana": dia,
                                                          "hora_inicio": "06:00", "hora_fim": "23:00"})
        return pid

    def paciente(self, apelido, telefone, autorizar=True, prioridade="NENHUMA"):
        p = self.post("/pacientes", {"nome": f"{apelido} da Silva", "telefone": telefone,
                                      "autorizar_contato": autorizar, "prioridade_assistencial": prioridade})
        p["tel"] = p["telefone"]
        self.pacientes[apelido] = p
        return p

    def agendar(self, paciente, data_hora=None, prof=None, esperado=201):
        return self.post("/agendamentos", {"paciente_id": paciente["id"], "unidade_id": self.unidade,
                                           "especialidade_id": self.esp, "profissional_id": prof or self.prof,
                                           "data_hora": data_hora or amanha_as(10)}, esperado)

    def fila(self, paciente, prioridade=None, preferencias=None, profissional_id=None, esperado=201):
        corpo = {"paciente_id": paciente["id"], "especialidade_id": self.esp,
                 "preferencias": preferencias if preferencias is not None else [{"unidade_id": self.unidade}]}
        if prioridade:
            corpo["prioridade"] = prioridade
        if profissional_id:
            corpo["profissional_id"] = profissional_id
        return self.post("/fila-espera", corpo, esperado)

    def get(self, rota, **params):
        r = self.c.get(f"/api/v1{rota}", headers=self.h, params=params)
        assert r.status_code == 200, r.text
        return r.json()

    def agendamento(self, ag_id):
        return self.get(f"/agendamentos/{ag_id}")


@pytest.fixture
def cenario(client, admin):
    return Cenario(client, admin)


@pytest.fixture
def com_lembrete_enviado(client, cenario):
    """Maria tem consulta amanhã e já recebeu o lembrete."""
    maria = cenario.paciente("Maria", "65999990001")
    ag = cenario.agendar(maria)
    rodar("lembretes")
    rodar("outbox")
    return maria, ag
