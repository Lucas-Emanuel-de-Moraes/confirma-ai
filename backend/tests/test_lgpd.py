"""HU04, UC11, UC12: consentimento, direitos do titular e retenção (RF21–RF23, RN17–RN19)."""

import pytest
from conftest import responder, rodar

from app.core import relogio
from app.core.database import SessionLocal
from app.modules.auditoria.models import LogAuditoria


def test_historico_de_consentimento(client, cenario):
    p = cenario.paciente("Maria", "65999990001", autorizar=False)
    h = cenario.h
    assert client.post(f"/api/v1/pacientes/{p['id']}/autorizacao", json={"origem": "formulario"}, headers=h).json()[
        "contato_autorizado"]
    client.delete(f"/api/v1/pacientes/{p['id']}/autorizacao", params={"motivo": "pediu"}, headers=h)
    client.put(f"/api/v1/pacientes/{p['id']}/preferencias-contato", json={"preferencias": {"periodo": "manha"}},
               headers=h)
    c = cenario.get(f"/pacientes/{p['id']}/consentimento")
    assert [x["acao"] for x in c["historico"]] == ["AUTORIZOU", "REVOGOU", "PREFERENCIAS"]
    assert c["autorizado"] is False and all(x["data_hora"] and x["origem"] for x in c["historico"])


def test_requisicao_de_acesso_e_correcao(client, cenario):
    p = cenario.paciente("Maria", "65999990001")
    cenario.agendar(p)
    req = cenario.post("/requisicoes-titular", {"paciente_id": p["id"], "tipo": "ACESSO"})
    r = client.patch(f"/api/v1/requisicoes-titular/{req['id']}", json={"acao": "RESOLVER"}, headers=cenario.h)
    assert r.status_code == 200 and r.json()["status"] == "RESOLVIDA"
    dados = r.json()["dados"]
    assert dados["paciente"]["nome"] == "Maria da Silva" and len(dados["agendamentos"]) == 1

    req = cenario.post("/requisicoes-titular", {"paciente_id": p["id"], "tipo": "CORRECAO",
                                                "dados_correcao": {"nome": "Maria Souza"}})
    client.patch(f"/api/v1/requisicoes-titular/{req['id']}", json={"acao": "RESOLVER"}, headers=cenario.h)
    assert cenario.get(f"/pacientes/{p['id']}")["nome"] == "Maria Souza"
    assert client.patch(f"/api/v1/requisicoes-titular/{req['id']}", json={}, headers=cenario.h).status_code == 409


def test_eliminacao_com_registros_obrigatorios_restringe(client, cenario):
    p = cenario.paciente("Maria", "65999990001")
    cenario.agendar(p)
    cenario.fila(p)
    req = cenario.post("/requisicoes-titular", {"paciente_id": p["id"], "tipo": "ELIMINACAO"})
    r = client.patch(f"/api/v1/requisicoes-titular/{req['id']}", json={"acao": "RESOLVER"}, headers=cenario.h).json()
    assert r["status"] == "RESOLVIDA_COM_RESTRICAO" and "RN18" in r["desfecho"]
    pac = cenario.get(f"/pacientes/{p['id']}")
    assert pac["uso_restrito"] and not pac["ativo"] and not pac["contato_autorizado"]
    assert pac["nome"] == "Maria da Silva"  # não eliminado
    assert cenario.get("/fila-espera")["total"] == 0


def test_eliminacao_sem_registros_anonimiza(client, cenario):
    p = cenario.paciente("Jose", "65999990005")
    req = cenario.post("/requisicoes-titular", {"paciente_id": p["id"], "tipo": "ELIMINACAO"})
    r = client.patch(f"/api/v1/requisicoes-titular/{req['id']}", json={"acao": "RESOLVER"}, headers=cenario.h).json()
    assert r["status"] == "RESOLVIDA"
    pac = cenario.get(f"/pacientes/{p['id']}")
    assert pac["anonimizado"] and pac["nome"].startswith("Paciente anonimizado") and pac["telefone"].startswith("anon")


def test_retencao_por_categoria(client, cenario, com_lembrete_enviado):
    maria, ag = com_lembrete_enviado
    responder(client, maria["tel"], "SIM", identificador="falso")  # tentativa inválida
    responder(client, maria["tel"], "SIM")
    cenario.post("/retencao/politicas", {}, esperado=405)
    r = client.put("/api/v1/retencao/politicas", headers=cenario.h, json=[
        {"categoria": "TENTATIVAS_INVALIDAS", "prazo_dias": 1},
        {"categoria": "MENSAGENS", "prazo_dias": 1},
    ])
    assert r.status_code == 200
    assert rodar("retencao")["TENTATIVAS_INVALIDAS"]["afetados"] == 0  # ainda dentro do prazo
    relogio.avancar(days=2)
    resultado = client.post("/api/v1/retencao/executar", headers=cenario.h).json()
    assert resultado["TENTATIVAS_INVALIDAS"]["afetados"] == 1
    assert resultado["MENSAGENS"]["afetados"] == 1
    assert cenario.agendamento(ag["id"])["status"] == "CONFIRMADO"  # agenda preservada
    logs = cenario.get("/auditoria", acao="RETENCAO_EXECUTADA")["itens"]
    assert len(logs) == 2 and logs[0]["detalhes"]["MENSAGENS"]["afetados"] == 1  # expurgo auditável (RN19)


def test_auditoria_somente_insercao(cenario):
    with SessionLocal() as db:
        log = db.query(LogAuditoria).first()
        log.acao = "ALTERADO"
        with pytest.raises(PermissionError):
            db.flush()
        db.rollback()
        with pytest.raises(PermissionError):
            db.delete(db.query(LogAuditoria).first())
            db.flush()
