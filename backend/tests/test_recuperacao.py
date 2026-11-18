"""UC05–UC07: elegibilidade, priorização, oferta com reserva, recusa, expiração e aceite (RF11–RF17)."""

from datetime import datetime

from conftest import amanha_as, mensagens_para, responder, rodar, ultima_mensagem

from app.core import relogio


def _liberar_vaga_da_maria(client, cenario):
    maria = cenario.paciente("Maria", "65999990001")
    ag = cenario.agendar(maria)
    rodar("lembretes")
    rodar("outbox")
    responder(client, maria["tel"], "NAO")
    return ag


def test_prioridade_assistencial_e_desempate(client, cenario):
    joao = cenario.paciente("Joao", "65999990002")
    ana = cenario.paciente("Ana", "65999990003")
    helena = cenario.paciente("Helena", "65999990004", prioridade="ALTA")
    cenario.fila(joao)
    cenario.fila(ana)
    cenario.fila(helena)  # entrou por último, mas tem prioridade ALTA (RN09)
    _liberar_vaga_da_maria(client, cenario)
    ofertas = cenario.get("/ofertas")["itens"]
    assert len(ofertas) == 1 and ofertas[0]["paciente"]["id"] == helena["id"]
    assert "prioridade=ALTA" in ofertas[0]["criterio_selecao"]
    # Helena recusa -> João (entrada mais antiga, RN10) recebe a próxima oferta
    rodar("outbox")
    responder(client, helena["tel"], "RECUSAR")
    ofertas = cenario.get("/ofertas", status="RESERVADA")["itens"]
    assert ofertas[0]["paciente"]["id"] == joao["id"]


def test_sem_prioridade_quando_regra_desliga(client, cenario):
    corpo = cenario.get(f"/unidades/{cenario.unidade}/parametros")
    corpo["considera_prioridade_assistencial"] = False
    r = client.put(f"/api/v1/unidades/{cenario.unidade}/parametros", json=corpo, headers=cenario.h)
    assert r.status_code == 200 and r.json()["versao"] == 2
    joao = cenario.paciente("Joao", "65999990002")
    helena = cenario.paciente("Helena", "65999990004", prioridade="ALTA")
    cenario.fila(joao)
    cenario.fila(helena)
    _liberar_vaga_da_maria(client, cenario)
    assert cenario.get("/ofertas")["itens"][0]["paciente"]["id"] == joao["id"]


def test_elegibilidade_filtra_incompativeis(client, cenario):
    nao_autorizado = cenario.paciente("Pedro", "65999990005", autorizar=False)
    noite = cenario.paciente("Lia", "65999990006")
    outra_unidade_id = cenario.post("/unidades", {"nome": "Unidade Norte"})["id"]
    longe = cenario.paciente("Rui", "65999990007")
    outro_prof = cenario.criar_profissional("Dr. Beto", "CRM 2")
    quer_outro = cenario.paciente("Sara", "65999990008")
    cenario.fila(nao_autorizado)
    cenario.fila(noite, preferencias=[{"unidade_id": cenario.unidade, "periodo": "NOITE"}])  # vaga é às 10h
    cenario.fila(longe, preferencias=[{"unidade_id": outra_unidade_id}])
    r = client.put(f"/api/v1/unidades/{cenario.unidade}",
                   json={"exige_profissional_especifico": True}, headers=cenario.h)
    assert r.status_code == 200
    cenario.fila(quer_outro, profissional_id=outro_prof)  # RN08: unidade exige o mesmo profissional
    _liberar_vaga_da_maria(client, cenario)
    assert cenario.get("/ofertas")["total"] == 0
    assert cenario.get("/vagas")["itens"][0]["status"] == "SEM_ELEGIVEIS"


def test_aceite_cria_novo_agendamento_e_sai_da_fila(client, cenario):
    joao = cenario.paciente("Joao", "65999990002")
    fila = cenario.fila(joao)
    ag = _liberar_vaga_da_maria(client, cenario)
    rodar("outbox")
    oferta_msg = ultima_mensagem(joao["tel"])
    assert oferta_msg["tipo"] == "OFERTA_ENCAIXE" and "Cardiologia" in oferta_msg["texto"]
    assert "Maria" not in oferta_msg["texto"]  # não expõe dados de outros pacientes (RF14)
    r = responder(client, joao["tel"], "ACEITAR")
    assert r["valida"]
    novo = cenario.agendamento(r["agendamento_id"])
    assert novo["paciente"]["id"] == joao["id"] and novo["data_hora"] == ag["data_hora"]
    assert novo["origem"] == "encaixe" and novo["status"] == "AGENDADO"  # o fluxo de lembrete recomeça
    assert cenario.get(f"/fila-espera/{fila['id']}")["ativo"] is False
    vaga = cenario.get("/vagas")["itens"][0]
    assert vaga["status"] == "PREENCHIDA" and vaga["agendamento_novo_id"] == novo["id"]
    # segunda tentativa de aceite (ex.: recepção) recebe 409 e não altera a agenda
    oferta_id = cenario.get("/ofertas")["itens"][0]["id"]
    r2 = client.post(f"/api/v1/ofertas/{oferta_id}/aceitar", headers=cenario.h)
    assert r2.status_code == 409
    assert cenario.get("/agendamentos")["total"] == 2


def test_reserva_bloqueia_horario_para_recepcao(client, cenario):
    joao, carlos = cenario.paciente("Joao", "65999990002"), cenario.paciente("Carlos", "65999990009")
    cenario.fila(joao)
    _liberar_vaga_da_maria(client, cenario)
    assert cenario.agendar(carlos, esperado=409)["codigo"] == "VAGA_RESERVADA"  # RN02


def test_oferta_expira_e_vai_para_o_proximo(client, cenario):
    joao, ana = cenario.paciente("Joao", "65999990002"), cenario.paciente("Ana", "65999990003")
    cenario.fila(joao)
    cenario.fila(ana)
    _liberar_vaga_da_maria(client, cenario)
    rodar("outbox")
    ident_joao = ultima_mensagem(joao["tel"])["identificador"]
    relogio.avancar(minutes=31)  # janela de reserva padrão: 30 min
    assert rodar("expirar-ofertas")["ofertas_expiradas"] == 1
    ofertas = {o["paciente"]["id"]: o["status"] for o in cenario.get("/ofertas")["itens"]}
    assert ofertas == {joao["id"]: "EXPIRADA", ana["id"]: "RESERVADA"}
    assert responder(client, joao["tel"], "ACEITAR", ident_joao)["motivo"] == "IDENTIFICADOR_EXPIRADO"


def test_vaga_fora_da_janela_nao_e_ofertada(client, cenario):
    joao = cenario.paciente("Joao", "65999990002")
    cenario.fila(joao)
    ag = cenario.agendar(cenario.paciente("Maria", "65999990001"), amanha_as(10))
    falta = datetime.fromisoformat(ag["data_hora"]) - relogio.agora()
    relogio.avancar(seconds=falta.total_seconds() - 3600)  # 1 h antes; antecedência mínima padrão = 120 min
    client.post(f"/api/v1/agendamentos/{ag['id']}/cancelar", json={"motivo": "em cima da hora"}, headers=cenario.h)
    vaga = cenario.get("/vagas")["itens"][0]
    assert vaga["status"] == "ENCERRADA" and cenario.get("/ofertas")["total"] == 0


def test_sem_elegiveis_e_nova_consulta_da_fila(client, cenario):
    _liberar_vaga_da_maria(client, cenario)
    assert cenario.get("/vagas")["itens"][0]["status"] == "SEM_ELEGIVEIS"
    joao = cenario.paciente("Joao", "65999990002")
    cenario.fila(joao)  # alguém entra na fila depois
    assert rodar("expirar-ofertas")["novas_ofertas"] == 1  # a tarefa periódica reavalia a vaga
    rodar("outbox")
    assert ultima_mensagem(joao["tel"])["tipo"] == "OFERTA_ENCAIXE"


def test_cancelamento_manual_da_oferta(client, cenario):
    joao = cenario.paciente("Joao", "65999990002")
    cenario.fila(joao)
    _liberar_vaga_da_maria(client, cenario)
    oferta = cenario.get("/ofertas")["itens"][0]
    r = client.post(f"/api/v1/ofertas/{oferta['id']}/cancelar",
                    json={"motivo": "tratado por telefone", "reofertar": False}, headers=cenario.h)
    assert r.status_code == 200 and r.json()["status"] == "CANCELADA"
    assert cenario.get("/vagas")["itens"][0]["status"] == "ENCERRADA"
    rodar("outbox")
    assert mensagens_para(joao["tel"]) == []  # a mensagem pendente foi cancelada
