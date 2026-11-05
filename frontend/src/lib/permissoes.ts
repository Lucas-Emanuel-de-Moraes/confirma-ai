import type { Perfil } from "./types";

// Espelha backend/app/modules/acesso/permissoes.py (menor privilégio, seção 5.3).
// O back-end continua sendo a autoridade: aqui só escondemos o que o perfil não pode usar.
export const P = {
  USUARIOS: "usuarios:gerenciar",
  PACIENTES_LER: "pacientes:ler",
  PACIENTES_ESCREVER: "pacientes:escrever",
  ESTRUTURA_LER: "estrutura:ler",
  ESTRUTURA_ESCREVER: "estrutura:escrever",
  AGENDA_LER: "agenda:ler",
  AGENDA_ESCREVER: "agenda:escrever",
  FILA_LER: "fila:ler",
  FILA_ESCREVER: "fila:escrever",
  OFERTAS_LER: "ofertas:ler",
  OFERTAS_GERENCIAR: "ofertas:gerenciar",
  PARAMETROS_LER: "parametros:ler",
  PARAMETROS_ESCREVER: "parametros:escrever",
  INDICADORES_LER: "indicadores:ler",
  TITULAR_GERENCIAR: "titular:gerenciar",
  RETENCAO_GERENCIAR: "retencao:gerenciar",
  AUDITORIA_LER: "auditoria:ler",
  TAREFAS_EXECUTAR: "tarefas:executar",
} as const;

export type Permissao = (typeof P)[keyof typeof P];

export const PERFIS_PADRAO: Record<Perfil, readonly string[]> = {
  ADMINISTRADOR: ["*"],
  GESTOR: [
    P.PACIENTES_LER, P.ESTRUTURA_LER, P.ESTRUTURA_ESCREVER, P.AGENDA_LER, P.FILA_LER,
    P.OFERTAS_LER, P.OFERTAS_GERENCIAR, P.PARAMETROS_LER, P.PARAMETROS_ESCREVER, P.INDICADORES_LER,
  ],
  RECEPCIONISTA: [
    P.PACIENTES_LER, P.PACIENTES_ESCREVER, P.ESTRUTURA_LER, P.AGENDA_LER, P.AGENDA_ESCREVER,
    P.FILA_LER, P.FILA_ESCREVER, P.OFERTAS_LER, P.OFERTAS_GERENCIAR, P.PARAMETROS_LER, P.TITULAR_GERENCIAR,
  ],
  PROFISSIONAL: [P.AGENDA_LER, P.ESTRUTURA_LER],
};

export function temPermissao(perfis: Perfil[] | undefined, permissao: Permissao): boolean {
  if (!perfis) return false;
  return perfis.some((p) => {
    const lista = PERFIS_PADRAO[p] ?? [];
    return lista.includes("*") || lista.includes(permissao);
  });
}
