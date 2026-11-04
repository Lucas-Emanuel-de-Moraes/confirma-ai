"""HU01 e UC01: pacientes, unidades, especialidades, profissionais, horários e bloqueios."""


def test_cadastrar_paciente_normaliza_telefone(cenario):
    p = cenario.paciente("Maria", "(65) 99999-0001")
    assert p["telefone"] == "5565999990001"
    assert p["contato_autorizado"] is True and p["ativo"] is True


def test_validacoes_do_paciente(client, admin):
    r = client.post("/api/v1/pacientes", json={"nome": "Jo", "telefone": "123"}, headers=admin)
    assert r.status_code == 422
    campos = {c["campo"] for c in r.json()["campos"]}
    assert {"nome", "telefone"} <= campos
    r = client.post("/api/v1/pacientes", json={"telefone": "65999990001"}, headers=admin)
    assert r.status_code == 422  # nome obrigatório


def test_aviso_de_telefone_duplicado(client, admin, cenario):
    cenario.paciente("Maria", "65999990001")
    r = client.post("/api/v1/pacientes", json={"nome": "Outra Pessoa", "telefone": "65999990001"}, headers=admin)
    assert r.status_code == 409 and r.json()["codigo"] == "TELEFONE_DUPLICADO"
    r = client.post("/api/v1/pacientes", json={"nome": "Outra Pessoa", "telefone": "65999990001",
                                               "ignorar_aviso_duplicidade": True}, headers=admin)
    assert r.status_code == 201


def test_inativar_sem_apagar_e_buscar(client, admin, cenario):
    p = cenario.paciente("Maria", "65999990001")
    cenario.paciente("Joao", "65999990002")
    r = client.patch(f"/api/v1/pacientes/{p['id']}/inativar", headers=admin)
    assert r.status_code == 200 and r.json()["ativo"] is False
    assert client.get(f"/api/v1/pacientes/{p['id']}", headers=admin).status_code == 200
    assert cenario.get("/pacientes", busca="maria")["total"] == 1
    assert cenario.get("/pacientes", ativo="true")["total"] == 1


def test_troca_de_telefone_exige_nova_autorizacao(client, admin, cenario):
    p = cenario.paciente("Maria", "65999990001")
    r = client.put(f"/api/v1/pacientes/{p['id']}", json={"telefone": "65988880001"}, headers=admin)
    assert r.status_code == 200 and r.json()["contato_autorizado"] is False


def test_estrutura_rejeita_duplicados_e_conflitos(client, admin, cenario):
    assert client.post("/api/v1/especialidades", json={"nome": "cardiologia"}, headers=admin).status_code == 409
    assert client.post("/api/v1/unidades", json={"nome": "Clínica Teste"}, headers=admin).status_code == 409
    r = client.post(f"/api/v1/profissionais/{cenario.prof}/horarios",
                    json={"unidade_id": cenario.unidade, "dia_semana": 0, "hora_inicio": "08:00", "hora_fim": "09:00"},
                    headers=admin)
    assert r.status_code == 409 and r.json()["codigo"] == "HORARIO_CONFLITANTE"
    outra = client.post("/api/v1/unidades", json={"nome": "Outra Unidade"}, headers=admin).json()["id"]
    r = client.post(f"/api/v1/profissionais/{cenario.prof}/horarios",
                    json={"unidade_id": outra, "dia_semana": 0, "hora_inicio": "08:00", "hora_fim": "09:00"},
                    headers=admin)
    assert r.status_code == 422  # profissional não vinculado a essa unidade


def test_unidade_cria_parametros_versao_1(cenario):
    p = cenario.get(f"/unidades/{cenario.unidade}/parametros")
    assert p["versao"] == 1 and p["antecedencia_lembrete_horas"] == 48
