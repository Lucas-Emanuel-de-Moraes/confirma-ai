import { Selo, type CorSelo } from "./ui";
import { rotulo } from "@/lib/formato";
import type { NivelPrioridade, StatusAgendamento, StatusOferta, StatusRemarcacao, StatusRequisicao, StatusVaga } from "@/lib/types";

const COR_AGENDAMENTO: Record<StatusAgendamento, CorSelo> = {
  AGENDADO: "cinza",
  AGUARDANDO_RESPOSTA: "azul",
  CONFIRMADO: "verde",
  NAO_CONFIRMADO: "vermelho",
  CANCELADO: "vermelho",
  REMARCACAO_SOLICITADA: "amarelo",
  SEM_RESPOSTA: "amarelo",
  REALIZADO: "verde",
  FALTA: "vermelho",
};
const COR_OFERTA: Record<StatusOferta, CorSelo> = {
  RESERVADA: "azul",
  ACEITA: "verde",
  RECUSADA: "vermelho",
  EXPIRADA: "amarelo",
  CANCELADA: "cinza",
  FALHA_CONTATO: "vermelho",
};
const COR_VAGA: Record<StatusVaga, CorSelo> = {
  DISPONIVEL: "azul",
  EM_OFERTA: "roxo",
  PREENCHIDA: "verde",
  SEM_ELEGIVEIS: "amarelo",
  ENCERRADA: "cinza",
};
const COR_REMARCACAO: Record<StatusRemarcacao, CorSelo> = { PENDENTE: "amarelo", REMARCADA: "verde", MANTIDA: "azul", CANCELADA: "cinza" };
const COR_REQUISICAO: Record<StatusRequisicao, CorSelo> = {
  ABERTA: "amarelo",
  RESOLVIDA: "verde",
  RESOLVIDA_COM_RESTRICAO: "azul",
  INDEFERIDA: "vermelho",
};
const COR_PRIORIDADE: Record<NivelPrioridade, CorSelo> = { NENHUMA: "cinza", BAIXA: "azul", MEDIA: "amarelo", ALTA: "vermelho" };

export const SeloAgendamento = ({ status, descricao }: { status: StatusAgendamento; descricao?: string }) => (
  <Selo cor={COR_AGENDAMENTO[status]} title={descricao}>
    {rotulo("statusAgendamento", status)}
  </Selo>
);
export const SeloOferta = ({ status }: { status: StatusOferta }) => <Selo cor={COR_OFERTA[status]}>{rotulo("statusOferta", status)}</Selo>;
export const SeloVaga = ({ status }: { status: StatusVaga }) => <Selo cor={COR_VAGA[status]}>{rotulo("statusVaga", status)}</Selo>;
export const SeloRemarcacao = ({ status }: { status: StatusRemarcacao }) => (
  <Selo cor={COR_REMARCACAO[status]}>{rotulo("statusRemarcacao", status)}</Selo>
);
export const SeloRequisicao = ({ status }: { status: StatusRequisicao }) => (
  <Selo cor={COR_REQUISICAO[status]}>{rotulo("statusRequisicao", status)}</Selo>
);
export const SeloPrioridade = ({ nivel }: { nivel: NivelPrioridade }) => (
  <Selo cor={COR_PRIORIDADE[nivel]}>{rotulo("prioridade", nivel)}</Selo>
);
export const SeloAtivo = ({ ativo }: { ativo: boolean }) => <Selo cor={ativo ? "verde" : "cinza"}>{ativo ? "Ativo" : "Inativo"}</Selo>;
