"""UC03, UC04, UC13: lembrete, resposta SIM/NÃO/REMARCAR e validação do vínculo (RF24, RN20, RNF19)."""

import json

from conftest import amanha_as, mensagens_para, responder, rodar, ultima_mensagem

from app.core import relogio


def test_lembrete_respeita_antecedencia(cenario):
    maria = cenario.paciente("Maria", "65999990001")
    cenario.agendar(maria, amanha_as(10, dias=5))  # 5 dias à frente; antecedência padrão = 48 h
    assert rodar("lembretes")["enfileirados"] == 0
    relogio.avancar(days=4)
    assert rodar("lembretes")["enfileirados"] == 1
    assert rodar("lembretes")["enfileirados"] == 0  # não duplica


def test_lembrete_discreto_e_status_aguardando(cenario, com_lembrete_enviado):
    maria, ag = com_lembrete_enviado
    msg = ultima_mensagem(maria["tel"])
    assert msg["tipo"] == "LEMBRETE_CONFIRMACAO" and msg["opcoes"] == ["SIM", "NAO", "REMARCAR"]
    assert "Cardiologia" not in msg["texto"]  # mensagem discreta (seção 5.3)
    assert len(msg["identificador"]) >= 20
    assert cenario.agendamento(ag["id"])["status"] == "AGUARDANDO_RESPOSTA"


def test_resposta_sim_confirma(client, cenario, com_lembrete_enviado):
    maria, ag = com_lembrete_enviado
    r = responder(client, maria["tel"], "Sim")
    assert r["valida"] and r["status"] == "CONFIRMADO"
    assert cenario.get("/vagas")["total"] == 0


def test_resposta_nao_libera_vaga(client, cenario, com_lembrete_enviado):
    maria, ag = com_lembrete_enviado
    assert responder(client, maria["tel"], "NÃO")["status"] == "NAO_CONFIRMADO"
    assert cenario.get("/vagas")["itens"][0]["motivo_liberacao"] == "NAO_CONFIRMADO"


def test_remarcar_nao_libera_vaga(client, cenario, com_lembrete_enviado):
    maria, ag = com_lembrete_enviado
    assert responder(client, maria["tel"], "remarcar")["status"] == "REMARCACAO_SOLICITADA"
    assert cenario.get("/vagas")["total"] == 0  # RN05
    pend = cenario.get("/remarcacoes")["itens"]
    assert len(pend) == 1 and pend[0]["agendamento"]["id"] == ag["id"]


def test_respostas_sem_vinculo_valido_sao_descartadas(client, cenario, com_lembrete_enviado):
    maria, ag = com_lembrete_enviado
    assert responder(client, maria["tel"], "SIM", identificador="inventado")["motivo"] == "IDENTIFICADOR_DESCONHECIDO"
    ident = ultima_mensagem(maria["tel"])["identificador"]
    assert responder(client, "65911112222", "SIM", identificador=ident)["motivo"] == "TELEFONE_DIVERGENTE"
    assert cenario.agendamento(ag["id"])["status"] == "AGUARDANDO_RESPOSTA"  # nada mudou
    assert responder(client, maria["tel"], "SIM", identificador=ident)["valida"]
    assert responder(client, maria["tel"], "NAO", identificador=ident)["motivo"] == "IDENTIFICADOR_JA_UTILIZADO"
    assert cenario.agendamento(ag["id"])["status"] == "CONFIRMADO"


def test_opcao_invalida_pede_nova_resposta(client, cenario, com_lembrete_enviado):
    maria, ag = com_lembrete_enviado
    ident = ultima_mensagem(maria["tel"])["identificador"]
    assert responder(client, maria["tel"], "talvez", identificador=ident)["motivo"] == "OPCAO_INVALIDA"
    rodar("outbox")
    assert "Não entendemos" in ultima_mensagem(maria["tel"])["texto"]
    assert responder(client, maria["tel"], "1", identificador=ident)["status"] == "CONFIRMADO"


def test_sem_resposta_no_prazo(client, cenario, com_lembrete_enviado):
    maria, ag = com_lembrete_enviado
    ident = ultima_mensagem(maria["tel"])["identificador"]
    relogio.avancar(minutes=721)  # prazo padrão: 720 min
    assert rodar("expirar-respostas")["sem_resposta"] == 1
    assert cenario.agendamento(ag["id"])["status"] == "SEM_RESPOSTA"
    assert cenario.get("/vagas")["itens"][0]["motivo_liberacao"] == "SEM_RESPOSTA"
    assert responder(client, maria["tel"], "SIM", identificador=ident)["motivo"] == "IDENTIFICADOR_EXPIRADO"


def test_webhook_exige_assinatura(client):
    corpo = json.dumps({"telefone": "5565999990001", "identificador": "x", "resposta": "SIM"})
    r = client.post("/api/v1/webhooks/mensageria", content=corpo, headers={"X-Assinatura": "errada"})
    assert r.status_code == 401 and r.json()["codigo"] == "ASSINATURA_INVALIDA"


def test_lembrete_bloqueado_sem_autorizacao(cenario):
    joao = cenario.paciente("Joao", "65999990002", autorizar=False)
    cenario.agendar(joao)
    assert rodar("lembretes") == {"enfileirados": 0, "bloqueados": 1}
    rodar("outbox")
    assert mensagens_para(joao["tel"]) == []
