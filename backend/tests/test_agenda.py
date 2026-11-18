"""UC02, RF03, RF04, RN01, RN14, RF17: registro e visualização da agenda."""

from conftest import amanha_as


def test_registrar_e_listar_com_status_textual(cenario):
    maria = cenario.paciente("Maria", "65999990001")
    ag = cenario.agendar(maria)
    assert ag["status"] == "AGENDADO" and ag["numero_agendamento"].startswith("AG")
    assert ag["status_descricao"]  # status por texto, não só por cor (RNF10)
    lista = cenario.get("/agendamentos", unidade_id=cenario.unidade, data=amanha_as(10)[:10])
    assert lista["total"] == 1 and lista["itens"][0]["paciente"]["nome"] == "Maria da Silva"
    assert cenario.get("/agendamentos", status="CONFIRMADO")["total"] == 0
    assert cenario.get("/agendamentos", busca="maria")["total"] == 1


def test_dupla_marcacao_bloqueada(cenario):
    maria, joao = cenario.paciente("Maria", "65999990001"), cenario.paciente("Joao", "65999990002")
    cenario.agendar(maria)
    r = cenario.agendar(joao, esperado=409)
    assert r["codigo"] == "HORARIO_OCUPADO" and "fila" in r["mensagem"]


def test_validacoes_de_disponibilidade(client, admin, cenario):
    maria = cenario.paciente("Maria", "65999990001")
    assert cenario.agendar(maria, amanha_as(23, 30), esperado=422)["codigo"] == "FORA_DO_HORARIO"
    assert cenario.agendar(maria, amanha_as(10, dias=-1), esperado=422)["campos"][0]["campo"] == "data_hora"
    # Bloqueio (feriado) na unidade – RN14
    cenario.post("/bloqueios", {"unidade_id": cenario.unidade, "inicio": amanha_as(0), "fim": amanha_as(23),
                                "tipo": "FERIADO", "motivo": "Feriado municipal"})
    assert cenario.agendar(maria, esperado=422)["codigo"] == "AGENDA_BLOQUEADA"


def test_profissional_sem_especialidade(client, admin, cenario):
    derma = cenario.post("/especialidades", {"nome": "Dermatologia"})["id"]
    maria = cenario.paciente("Maria", "65999990001")
    r = client.post("/api/v1/agendamentos", headers=admin, json={
        "paciente_id": maria["id"], "unidade_id": cenario.unidade, "especialidade_id": derma,
        "profissional_id": cenario.prof, "data_hora": amanha_as(10)})
    assert r.status_code == 422


def test_cancelar_pela_recepcao_libera_vaga(client, admin, cenario):
    maria = cenario.paciente("Maria", "65999990001")
    ag = cenario.agendar(maria)
    r = client.post(f"/api/v1/agendamentos/{ag['id']}/cancelar", json={"motivo": "Paciente ligou"}, headers=admin)
    assert r.status_code == 200 and r.json()["status"] == "CANCELADO"
    vagas = cenario.get("/vagas")["itens"]
    assert len(vagas) == 1 and vagas[0]["status"] == "SEM_ELEGIVEIS"  # fila vazia
    # o horário liberado pode ser ocupado de novo (índice parcial) e conta como vaga recuperada
    joao = cenario.paciente("Joao", "65999990002")
    cenario.agendar(joao)
    assert cenario.get("/vagas")["itens"][0]["status"] == "PREENCHIDA"


def test_transicao_invalida(client, admin, cenario):
    ag = cenario.agendar(cenario.paciente("Maria", "65999990001"))
    client.post(f"/api/v1/agendamentos/{ag['id']}/cancelar", json={"motivo": "teste"}, headers=admin)
    r = client.post(f"/api/v1/agendamentos/{ag['id']}/cancelar", json={"motivo": "de novo"}, headers=admin)
    assert r.status_code == 422 and r.json()["codigo"] == "TRANSICAO_INVALIDA"


def test_historico_do_agendamento(cenario):
    ag = cenario.agendar(cenario.paciente("Maria", "65999990001"))
    eventos = cenario.get(f"/agendamentos/{ag['id']}/historico")
    assert eventos[0]["tipo"] == "STATUS" and "AGENDADO" in eventos[0]["descricao"]
