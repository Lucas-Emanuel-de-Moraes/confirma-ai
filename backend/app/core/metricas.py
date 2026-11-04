"""Métricas de observabilidade expostas em /metrics no formato Prometheus (RNF18)."""

from prometheus_client import Counter

MENSAGENS_ENVIADAS = Counter(
    "confirma_mensagens_enviadas_total", "Mensagens entregues ao provedor de mensageria", ["tipo"]
)
MENSAGENS_FALHAS = Counter(
    "confirma_mensagens_falhas_total", "Falhas no envio de mensagens", ["tipo", "definitiva"]
)
RESPOSTAS_RECEBIDAS = Counter(
    "confirma_respostas_recebidas_total", "Respostas recebidas dos pacientes", ["tipo", "valida"]
)
CONFIRMACOES = Counter("confirma_confirmacoes_total", "Consultas confirmadas pelo paciente")
VAGAS_LIBERADAS = Counter("confirma_vagas_liberadas_total", "Vagas liberadas para recuperação")
VAGAS_RECUPERADAS = Counter("confirma_vagas_recuperadas_total", "Vagas reaproveitadas por encaixe")
