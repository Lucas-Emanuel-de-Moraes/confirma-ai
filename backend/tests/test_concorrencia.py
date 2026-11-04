"""UC07 / RF17 / RNF03: duas operações simultâneas sobre a mesma vaga – só uma pode vencer.

Estes testes precisam de PostgreSQL (bloqueio de linha real). Com SQLite eles são pulados.
"""

import threading

import pytest
from conftest import EH_POSTGRES, amanha_as, responder, rodar
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.core.erros import Conflito
from app.modules.recuperacao import service as recuperacao
from app.modules.recuperacao.models import OfertaVaga, StatusOferta

pytestmark = pytest.mark.skipif(not EH_POSTGRES, reason="requer PostgreSQL (defina TEST_DATABASE_URL)")


def _em_paralelo(funcao, n=2):
    barreira = threading.Barrier(n)
    resultados = []

    def rodar_uma(i):
        barreira.wait()
        resultados.append(funcao(i))

    threads = [threading.Thread(target=rodar_uma, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return resultados


def _oferta_reservada(client, cenario):
    joao = cenario.paciente("Joao", "65999990002")
    cenario.fila(joao)
    maria = cenario.paciente("Maria", "65999990001")
    cenario.agendar(maria)
    rodar("lembretes")
    rodar("outbox")
    responder(client, maria["tel"], "NAO")
    return cenario.get("/ofertas")["itens"][0]["id"]


def test_dois_aceites_simultaneos_da_mesma_oferta(client, cenario):
    oferta_id = _oferta_reservada(client, cenario)

    def aceitar(_):
        with SessionLocal() as db:
            try:
                recuperacao.aceitar_oferta(db, oferta_id, "teste")
                db.commit()
                return "ok"
            except Conflito:
                db.rollback()
                return "409"

    assert sorted(_em_paralelo(aceitar, 4)) == ["409", "409", "409", "ok"]
    assert cenario.get("/agendamentos", status="AGENDADO")["total"] == 1


def test_indice_parcial_impede_segunda_reserva(client, cenario):
    oferta_id = _oferta_reservada(client, cenario)
    with SessionLocal() as db:
        o = db.get(OfertaVaga, oferta_id)
        copia = OfertaVaga(vaga_id=o.vaga_id, agendamento_id=o.agendamento_id, paciente_id=o.paciente_id,
                           fila_id=o.fila_id, vaga_data_hora=o.vaga_data_hora, status=StatusOferta.RESERVADA,
                           prazo_resposta=o.prazo_resposta, reserva_ativa=True, data_criacao=o.data_criacao)
        db.add(copia)
        with pytest.raises(IntegrityError):
            db.commit()


def test_agendamentos_simultaneos_no_mesmo_horario(client, cenario):
    pacientes = [cenario.paciente(f"P{i}", f"6599999100{i}") for i in range(4)]
    data = amanha_as(9)

    def agendar(i):
        r = client.post("/api/v1/agendamentos", headers=cenario.h, json={
            "paciente_id": pacientes[i]["id"], "unidade_id": cenario.unidade, "especialidade_id": cenario.esp,
            "profissional_id": cenario.prof, "data_hora": data})
        return r.status_code

    assert sorted(_em_paralelo(agendar, 4)) == [201, 409, 409, 409]
