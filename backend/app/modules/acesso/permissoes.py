"""Perfis padrão e suas permissões (menor privilégio, seção 5.3).

O perfil Administrador tem "*" (todas). Os demais recebem apenas o necessário à função.
"""

USUARIOS = "usuarios:gerenciar"
PACIENTES_LER = "pacientes:ler"
PACIENTES_ESCREVER = "pacientes:escrever"
ESTRUTURA_LER = "estrutura:ler"
ESTRUTURA_ESCREVER = "estrutura:escrever"
AGENDA_LER = "agenda:ler"
AGENDA_ESCREVER = "agenda:escrever"
FILA_LER = "fila:ler"
FILA_ESCREVER = "fila:escrever"
OFERTAS_LER = "ofertas:ler"
OFERTAS_GERENCIAR = "ofertas:gerenciar"
PARAMETROS_LER = "parametros:ler"
PARAMETROS_ESCREVER = "parametros:escrever"
INDICADORES_LER = "indicadores:ler"
TITULAR_GERENCIAR = "titular:gerenciar"
RETENCAO_GERENCIAR = "retencao:gerenciar"
AUDITORIA_LER = "auditoria:ler"
TAREFAS_EXECUTAR = "tarefas:executar"

ADMINISTRADOR = "ADMINISTRADOR"
GESTOR = "GESTOR"
RECEPCIONISTA = "RECEPCIONISTA"
PROFISSIONAL = "PROFISSIONAL"

PERFIS_PADRAO: dict[str, list[str]] = {
    ADMINISTRADOR: ["*"],
    GESTOR: [
        PACIENTES_LER, ESTRUTURA_LER, ESTRUTURA_ESCREVER, AGENDA_LER, FILA_LER,
        OFERTAS_LER, OFERTAS_GERENCIAR, PARAMETROS_LER, PARAMETROS_ESCREVER, INDICADORES_LER,
    ],
    RECEPCIONISTA: [
        PACIENTES_LER, PACIENTES_ESCREVER, ESTRUTURA_LER, AGENDA_LER, AGENDA_ESCREVER,
        FILA_LER, FILA_ESCREVER, OFERTAS_LER, OFERTAS_GERENCIAR, PARAMETROS_LER, TITULAR_GERENCIAR,
    ],
    PROFISSIONAL: [AGENDA_LER, ESTRUTURA_LER],
}
