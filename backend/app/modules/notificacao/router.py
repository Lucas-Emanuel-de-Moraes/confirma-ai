"""Endpoints do simulador de mensageria – existem apenas com MENSAGERIA_PROVEDOR=simulador.

Servem para testar o fluxo na própria máquina, sem WhatsApp: ver as mensagens que o
sistema "enviou" e responder como se fosse o paciente.
"""

import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.erros import NaoEncontrado
from app.modules.notificacao.gateway import obter_gateway
from app.modules.notificacao.simulador import SimuladorGateway, assinar

router = APIRouter(prefix="/simulador", tags=["Simulador de mensageria (desenvolvimento)"])


class RespostaSimulada(BaseModel):
    telefone: str = Field(examples=["5565999991234"])
    identificador: str | None = Field(default=None, description="Identificador recebido na mensagem")
    resposta: str = Field(examples=["SIM"], description="SIM, NAO, REMARCAR, ACEITAR, RECUSAR ou SAIR")


def _simulador() -> SimuladorGateway:
    gw = obter_gateway()
    if not isinstance(gw, SimuladorGateway):
        raise NaoEncontrado("O simulador só está disponível com MENSAGERIA_PROVEDOR=simulador.")
    return gw


@router.get("/mensagens", summary="Caixa de saída do simulador (mensagens enviadas aos pacientes)")
def mensagens(telefone: str | None = None, limite: int = 20):
    itens = list(_simulador().caixa_saida)
    if telefone:
        itens = [m for m in itens if m["destino"].endswith(telefone[-8:])]
    return list(reversed(itens))[:limite]


@router.post("/responder", summary="Simula a resposta do paciente (envia ao webhook assinado)")
def responder(dados: RespostaSimulada, db: Session = Depends(get_db)):
    from app.modules.confirmacao import service as confirmacao

    _simulador()
    corpo = json.dumps(dados.model_dump()).encode()
    headers = {"x-assinatura": assinar(corpo)}
    return confirmacao.receber_webhook(db, corpo, headers)
