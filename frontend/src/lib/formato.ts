// A API trabalha com data/hora local da clínica, sem fuso (ex.: "2026-11-10T09:00:00").

const pad = (n: number) => String(n).padStart(2, "0");

function partes(valor: string) {
  const m = valor.match(/^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2}))?/);
  if (!m) return null;
  return { ano: m[1], mes: m[2], dia: m[3], hora: m[4], min: m[5] };
}

export function dataHora(valor: string | null | undefined): string {
  if (!valor) return "—";
  const p = partes(valor);
  if (!p) return valor;
  return p.hora ? `${p.dia}/${p.mes}/${p.ano} ${p.hora}:${p.min}` : `${p.dia}/${p.mes}/${p.ano}`;
}

export function data(valor: string | null | undefined): string {
  if (!valor) return "—";
  const p = partes(valor);
  return p ? `${p.dia}/${p.mes}/${p.ano}` : valor;
}

export function hora(valor: string | null | undefined): string {
  if (!valor) return "—";
  const p = partes(valor);
  if (p?.hora) return `${p.hora}:${p.min}`;
  return valor.slice(0, 5);
}

const paraISO = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

/**
 * "AAAA-MM-DD" do dia de hoje (local).
 * Lê o relógio: não chame durante a renderização (o Next pré-renderiza Client Components).
 * Em componentes, use o hook `useHoje()`.
 */
export function hojeISO(): string {
  return paraISO(new Date());
}

/** Soma (ou subtrai) dias a uma data "AAAA-MM-DD" sem ler o relógio. */
export function somarDias(iso: string, dias: number): string {
  const [ano, mes, dia] = iso.split("-").map(Number);
  return paraISO(new Date(ano, mes - 1, dia + dias));
}

/** Valor de <input type="datetime-local"> → formato aceito pela API. */
export function paraApiDataHora(valorInput: string): string {
  return valorInput.length === 16 ? `${valorInput}:00` : valorInput;
}

/** Valor vindo da API → <input type="datetime-local">. */
export function paraInputDataHora(valorApi: string | null | undefined): string {
  return valorApi ? valorApi.slice(0, 16) : "";
}

export function percentual(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  // A API devolve frações (0.85 = 85%)
  return `${(v * 100).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;
}

export function telefone(v: string | null | undefined): string {
  if (!v) return "—";
  const d = v.replace(/\D/g, "");
  const local = d.startsWith("55") && d.length >= 12 ? d.slice(2) : d;
  if (local.length === 11) return `(${local.slice(0, 2)}) ${local.slice(2, 7)}-${local.slice(7)}`;
  if (local.length === 10) return `(${local.slice(0, 2)}) ${local.slice(2, 6)}-${local.slice(6)}`;
  return v;
}

export const DIAS_SEMANA = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"];

export const ROTULOS: Record<string, Record<string, string>> = {
  statusAgendamento: {
    AGENDADO: "Agendado",
    AGUARDANDO_RESPOSTA: "Aguardando resposta",
    CONFIRMADO: "Confirmado",
    NAO_CONFIRMADO: "Não confirmado",
    CANCELADO: "Cancelado",
    REMARCACAO_SOLICITADA: "Remarcação solicitada",
    SEM_RESPOSTA: "Sem resposta",
    REALIZADO: "Realizado",
    FALTA: "Falta",
  },
  statusOferta: {
    RESERVADA: "Reservada",
    ACEITA: "Aceita",
    RECUSADA: "Recusada",
    EXPIRADA: "Expirada",
    CANCELADA: "Cancelada",
    FALHA_CONTATO: "Falha de contato",
  },
  statusVaga: {
    DISPONIVEL: "Disponível",
    EM_OFERTA: "Em oferta",
    PREENCHIDA: "Preenchida",
    SEM_ELEGIVEIS: "Sem elegíveis",
    ENCERRADA: "Encerrada",
  },
  statusRemarcacao: {
    PENDENTE: "Pendente",
    REMARCADA: "Remarcada",
    MANTIDA: "Mantida",
    CANCELADA: "Cancelada",
  },
  statusRequisicao: {
    ABERTA: "Aberta",
    RESOLVIDA: "Resolvida",
    RESOLVIDA_COM_RESTRICAO: "Resolvida com restrição",
    INDEFERIDA: "Indeferida",
  },
  tipoRequisicao: {
    CONFIRMACAO_TRATAMENTO: "Confirmação de tratamento",
    ACESSO: "Acesso aos dados",
    CORRECAO: "Correção de dados",
    ELIMINACAO: "Eliminação de dados",
  },
  prioridade: { NENHUMA: "Nenhuma", BAIXA: "Baixa", MEDIA: "Média", ALTA: "Alta" },
  periodo: { MANHA: "Manhã", TARDE: "Tarde", NOITE: "Noite", QUALQUER: "Qualquer" },
  tipoBloqueio: { FERIADO: "Feriado", INDISPONIBILIDADE: "Indisponibilidade", OUTRO: "Outro" },
  categoriaDado: {
    MENSAGENS: "Mensagens enviadas",
    RESPOSTAS: "Respostas recebidas",
    TENTATIVAS_INVALIDAS: "Tentativas inválidas",
    FILA_ESPERA_ENCERRADA: "Fila de espera encerrada",
    PACIENTES_INATIVOS: "Pacientes inativos",
  },
  acaoRetencao: { ELIMINAR: "Eliminar", ANONIMIZAR: "Anonimizar" },
  perfil: {
    ADMINISTRADOR: "Administrador",
    GESTOR: "Gestor",
    RECEPCIONISTA: "Recepcionista",
    PROFISSIONAL: "Profissional",
  },
};

export function rotulo(grupo: keyof typeof ROTULOS | string, valor: string | null | undefined): string {
  if (!valor) return "—";
  return ROTULOS[grupo]?.[valor] ?? valor;
}

export function opcoes(grupo: string): { value: string; label: string }[] {
  return Object.entries(ROTULOS[grupo] ?? {}).map(([value, label]) => ({ value, label }));
}
