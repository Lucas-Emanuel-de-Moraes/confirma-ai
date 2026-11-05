"use client";

import { useState } from "react";
import { useAcao, useConsulta } from "@/hooks/useApi";
import { useCadastros } from "@/hooks/useCadastros";
import { useAuth } from "@/lib/auth";
import { P } from "@/lib/permissoes";
import { api } from "@/lib/api";
import { dataHora } from "@/lib/formato";
import type { Parametros } from "@/lib/types";
import { ExigePermissao } from "@/components/AppShell";
import { Alerta, Botao, CabecalhoPagina, Caixa, Cartao, Entrada, Selecao, Selo } from "@/components/ui";
import { Tabela } from "@/components/ui/Tabela";
import { useAvisos } from "@/components/ui/Aviso";

export default function ParametrosPage() {
  return (
    <ExigePermissao permissao={P.PARAMETROS_LER}>
      <Conteudo />
    </ExigePermissao>
  );
}

type Form = Omit<Parametros, "unidade_id" | "versao" | "vigente" | "criado_em" | "criado_por_id">;

const CAMPOS_NUMERICOS: { chave: keyof Form; rotulo: string; ajuda: string }[] = [
  { chave: "antecedencia_lembrete_horas", rotulo: "Antecedência do lembrete (horas)", ajuda: "Quanto tempo antes da consulta o lembrete é enviado." },
  { chave: "prazo_resposta_min", rotulo: "Prazo de resposta ao lembrete (min)", ajuda: "Depois disso o agendamento fica sem resposta." },
  { chave: "tentativas_contato", rotulo: "Tentativas de contato", ajuda: "Reenvios em caso de falha." },
  { chave: "janela_reserva_min", rotulo: "Janela de reserva da oferta (min)", ajuda: "Tempo que a vaga fica reservada aguardando aceite." },
  { chave: "antecedencia_minima_oferta_min", rotulo: "Antecedência mínima para ofertar (min)", ajuda: "Não oferta vagas muito próximas do horário." },
];

function paraForm(p: Parametros): Form {
  return {
    antecedencia_lembrete_horas: p.antecedencia_lembrete_horas,
    prazo_resposta_min: p.prazo_resposta_min,
    tentativas_contato: p.tentativas_contato,
    janela_reserva_min: p.janela_reserva_min,
    antecedencia_minima_oferta_min: p.antecedencia_minima_oferta_min,
    nome_regra: p.nome_regra,
    considera_prioridade_assistencial: p.considera_prioridade_assistencial,
    exige_profissional_compativel: p.exige_profissional_compativel,
    criterio_desempate: p.criterio_desempate,
  };
}

function Conteudo() {
  const { pode } = useAuth();
  const avisar = useAvisos();
  const { unidades } = useCadastros();
  const [unidadeId, setUnidadeId] = useState("");
  const id = unidadeId || (unidades[0] ? String(unidades[0].id) : "");
  const vigente = useConsulta<Parametros>(id ? `/unidades/${id}/parametros` : null);
  const historico = useConsulta<Parametros[]>(id ? `/unidades/${id}/parametros/historico` : null);
  const [form, setForm] = useState<Form | null>(null);
  const [base, setBase] = useState<Parametros | null>(null);

  if (vigente.dados && vigente.dados !== base) {
    setBase(vigente.dados);
    setForm(paraForm(vigente.dados));
  }

  const salvar = useAcao(async () => {
    if (!form) return;
    await api.put(`/unidades/${id}/parametros`, form);
    avisar("Nova versão dos parâmetros criada.");
    void vigente.recarregar();
    void historico.recarregar();
  });
  const escrever = pode(P.PARAMETROS_ESCREVER);

  return (
    <>
      <CabecalhoPagina
        titulo="Parâmetros operacionais"
        descricao="Regras de lembrete, prazos e elegibilidade por unidade. Cada alteração cria uma nova versão (UC10)."
      />
      <div className="mb-4 max-w-sm">
        <Selecao rotulo="Unidade" value={id} onChange={(e) => setUnidadeId(e.target.value)} opcoes={unidades.map((u) => ({ value: u.id, label: u.nome }))} />
      </div>
      {(vigente.erro || salvar.erro) && <Alerta onFechar={salvar.limparErro}>{vigente.erro ?? salvar.erro}</Alerta>}

      {form && vigente.dados && (
        <div className="grid gap-6 lg:grid-cols-3">
          <Cartao titulo={`Versão vigente: v${vigente.dados.versao}`} className="lg:col-span-2">
            <form className="space-y-4" onSubmit={(e) => (e.preventDefault(), void salvar.executar())}>
              <fieldset disabled={!escrever} className="grid gap-4 sm:grid-cols-2">
                {CAMPOS_NUMERICOS.map((c) => (
                  <Entrada
                    key={c.chave}
                    rotulo={c.rotulo}
                    ajuda={c.ajuda}
                    type="number"
                    min={0}
                    value={String(form[c.chave])}
                    onChange={(e) => setForm({ ...form, [c.chave]: Number(e.target.value) })}
                  />
                ))}
                <Entrada rotulo="Nome da regra" value={form.nome_regra} onChange={(e) => setForm({ ...form, nome_regra: e.target.value })} />
                <Selecao
                  rotulo="Critério de desempate"
                  value={form.criterio_desempate}
                  onChange={(e) => setForm({ ...form, criterio_desempate: e.target.value as Form["criterio_desempate"] })}
                  opcoes={[
                    { value: "DATA_ENTRADA", label: "Data de entrada na fila" },
                    { value: "ID", label: "Ordem de cadastro (ID)" },
                  ]}
                />
                <Caixa
                  rotulo="Considerar prioridade assistencial"
                  checked={form.considera_prioridade_assistencial}
                  onChange={(e) => setForm({ ...form, considera_prioridade_assistencial: e.target.checked })}
                />
                <Caixa
                  rotulo="Exigir profissional compatível"
                  checked={form.exige_profissional_compativel}
                  onChange={(e) => setForm({ ...form, exige_profissional_compativel: e.target.checked })}
                />
              </fieldset>
              {escrever && (
                <Botao type="submit" carregando={salvar.executando}>
                  Salvar nova versão
                </Botao>
              )}
            </form>
          </Cartao>
          <Cartao titulo="Histórico de versões">
            <Tabela
              itens={historico.dados ?? undefined}
              carregando={historico.carregando}
              chave={(p) => p.versao}
              colunas={[
                { titulo: "Versão", render: (p) => <span className="font-medium">v{p.versao}</span> },
                { titulo: "Criada em", render: (p) => dataHora(p.criado_em) },
                { titulo: "", render: (p) => p.vigente && <Selo cor="verde">Vigente</Selo> },
              ]}
            />
          </Cartao>
        </div>
      )}
    </>
  );
}
