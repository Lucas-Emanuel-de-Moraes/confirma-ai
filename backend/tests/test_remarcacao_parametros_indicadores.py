"""HU02 (remarcação), UC10 (parâmetros versionados) e UC09 (indicadores)."""

from conftest import amanha_as, login, responder, rodar


def _pedir_remarcacao(client, cenario, com_lembrete_enviado):
    maria, ag = com_lembrete_enviado
    responder(client, maria["tel"], "REMARCAR")
    return maria, ag, cenario.get("/remarcacoes")["itens"][0]


def test_remarcar_cria_novo_e_libera_original(client, cenario, com_lembrete_enviado):
    maria, ag, sol = _pedir_remarcacao(client, cenario, com_lembrete_enviado)
    r = client.patch(f"/api/v1/remarcacoes/{sol['id']}", headers=cenario.h,
                     json={"acao": "REMARCAR", "nova_data_hora": amanha_as(15, dias=3)})
    assert r.status_code == 200 and r.json()["status"] == "REMARCADA"
    novo = cenario.agendamento(r.json()["novo_agendamento_id"])
    assert novo["origem"] == "remarcacao" and novo["paciente"]["id"] == maria["id"]
    assert cenario.agendamento(ag["id"])["status"] == "CANCELADO"
    assert cenario.get("/vagas")["total"] == 1
    assert cenario.get("/remarcacoes")["total"] == 0


def test_manter_consulta(client, cenario, com_lembrete_enviado):
    maria, ag, sol = _pedir_remarcacao(client, cenario, com_lembrete_enviado)
    client.patch(f"/api/v1/remarcacoes/{sol['id']}", json={"acao": "MANTER"}, headers=cenario.h)
    assert cenario.agendamento(ag["id"])["status"] == "CONFIRMADO"


def test_cancelar_e_incluir_na_fila(client, cenario, com_lembrete_enviado):
    maria, ag, sol = _pedir_remarcacao(client, cenario, com_lembrete_enviado)
    r = client.patch(f"/api/v1/remarcacoes/{sol['id']}", headers=cenario.h,
                     json={"acao": "CANCELAR", "incluir_fila_espera": True})
    assert r.json()["status"] == "CANCELADA"
    fila = cenario.get("/fila-espera")["itens"]
    assert len(fila) == 1 and fila[0]["paciente"]["id"] == maria["id"]


def test_remarcar_exige_data(client, cenario, com_lembrete_enviado):
    _, _, sol = _pedir_remarcacao(client, cenario, com_lembrete_enviado)
    r = client.patch(f"/api/v1/remarcacoes/{sol['id']}", json={"acao": "REMARCAR"}, headers=cenario.h)
    assert r.status_code == 422


def test_parametros_versionados_e_validados(client, cenario):
    url = f"/api/v1/unidades/{cenario.unidade}/parametros"
    base = cenario.get(f"/unidades/{cenario.unidade}/parametros")
    assert client.put(url, json={**base, "tentativas_contato": 0}, headers=cenario.h).status_code == 422
    assert client.put(url, json={**base, "prazo_resposta_min": 4000, "antecedencia_lembrete_horas": 24},
                      headers=cenario.h).status_code == 422
    assert client.put(url, json={**base, "janela_reserva_min": 15}, headers=cenario.h).json()["versao"] == 2
    hist = cenario.get(f"/unidades/{cenario.unidade}/parametros/historico")
    assert [h["versao"] for h in hist] == [2, 1] and [h["vigente"] for h in hist] == [True, False]
    recep = login(client, "admin")  # recepção só lê; quem altera é gestor ou admin
    assert client.get(url, headers=recep).status_code == 200


def test_indicadores(client, cenario):
    joao, ana = cenario.paciente("Joao", "65999990002"), cenario.paciente("Ana", "65999990003")
    cenario.fila(joao)
    maria = cenario.paciente("Maria", "65999990001")
    cenario.agendar(maria, amanha_as(10))
    cenario.agendar(ana, amanha_as(11))
    rodar("lembretes")
    rodar("outbox")
    responder(client, maria["tel"], "NAO")
    responder(client, ana["tel"], "SIM")
    rodar("outbox")
    responder(client, joao["tel"], "ACEITAR")
    d = cenario.get("/indicadores")
    assert d["agendamentos"]["total"] == 3 and d["agendamentos"]["confirmados"] == 1
    assert d["agendamentos"]["cancelados"] == 1
    assert d["vagas"]["liberadas"] == 1 and d["vagas"]["recuperadas"] == 1
    assert d["taxas"]["taxa_recuperacao"] == 1.0 and d["taxas"]["taxa_ocupacao"] == 1.0
    assert d["ofertas"]["ACEITA"] == 1
