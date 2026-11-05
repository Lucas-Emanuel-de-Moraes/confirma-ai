"use client";

import { useState } from "react";
import { useAcao, useConsulta } from "@/hooks/useApi";
import { useCadastros } from "@/hooks/useCadastros";
import { useAuth } from "@/lib/auth";
import { P } from "@/lib/permissoes";
import { api } from "@/lib/api";
import { dataHora, opcoes, paraApiDataHora } from "@/lib/formato";
import type { Pagina, Remarcacao } from "@/lib/types";
import { ExigePermissao } from "@/components/AppShell";
import { Alerta, AreaTexto, BarraFiltros, Botao, CabecalhoPagina, Caixa, Cartao, Entrada, ItemDefinicao, Selecao } from "@/components/ui";
import { Modal } from "@/components/ui/Modal";
import { Paginacao, Tabela } from "@/components/ui/Tabela";
import { useAvisos } from "@/components/ui/Aviso";
import { SeloAgendamento, SeloRemarcacao } from "@/components/Status";

export default function RemarcacoesPage() {
  return (
    <ExigePermissao permissao={P.AGENDA_LER}>
      <Conteudo />
    </ExigePermissao>
  );
}

function Conteudo() {
  const { pode } = useAuth();
  const [status, setStatus] = useState("PENDENTE");
  const [page, setPage] = useState(1);
  const lista = useConsulta<Pagina<Remarcacao>>("/remarcacoes", { status, page, size: 20 });
  const [alvo, setAlvo] = useState<Remarcacao | null>(null);

  return (
    <>
      <CabecalhoPagina
        titulo="Remarcações"
        descricao="Pacientes que responderam REMARCAR. A recepção decide se remarca, mantém ou cancela (HU02)."
      />
      <BarraFiltros>
        <Selecao
          rotulo="Situação"
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setPage(1);
          }}
          opcoes={opcoes("statusRemarcacao")}
        />
      </BarraFiltros>
      {lista.erro && <Alerta>{lista.erro}</Alerta>}
      <Cartao>
        <Tabela
          itens={lista.dados?.itens}
          carregando={lista.carregando}
          chave={(r) => r.id}
          onLinha={pode(P.AGENDA_ESCREVER) && status === "PENDENTE" ? setAlvo : undefined}
          vazio="Nenhuma solicitação nesta situação."
          colunas={[
            { titulo: "Solicitado em", render: (r) => dataHora(r.data_solicitacao) },
            { titulo: "Paciente", render: (r) => <span className="font-medium">{r.agendamento.paciente.nome}</span> },
            { titulo: "Consulta original", render: (r) => `${dataHora(r.agendamento.data_hora)} · ${r.agendamento.profissional.nome}` },
            { titulo: "Agendamento", render: (r) => <SeloAgendamento status={r.agendamento.status} /> },
            { titulo: "Situação", render: (r) => <SeloRemarcacao status={r.status} /> },
            { titulo: "Origem", render: (r) => r.origem },
          ]}
        />
        {lista.dados && <Paginacao {...lista.dados} onPage={setPage} />}
      </Cartao>
      <Resolver
        remarcacao={alvo}
        onFechar={() => setAlvo(null)}
        onSalvo={() => {
          setAlvo(null);
          void lista.recarregar();
        }}
      />
    </>
  );
}

function Resolver({ remarcacao, onFechar, onSalvo }: { remarcacao: Remarcacao | null; onFechar: () => void; onSalvo: () => void }) {
  const avisar = useAvisos();
  const { profissionais } = useCadastros();
  const [form, setForm] = useState({ acao: "REMARCAR", nova_data_hora: "", novo_profissional_id: "", incluir_fila_espera: false, observacao: "" });
  const salvar = useAcao(async () => {
    if (!remarcacao) return;
    await api.patch(`/remarcacoes/${remarcacao.id}`, {
      acao: form.acao,
      nova_data_hora: form.acao === "REMARCAR" ? paraApiDataHora(form.nova_data_hora) : null,
      novo_profissional_id: form.acao === "REMARCAR" && form.novo_profissional_id ? Number(form.novo_profissional_id) : null,
      incluir_fila_espera: form.acao === "CANCELAR" && form.incluir_fila_espera,
      observacao: form.observacao || null,
    });
    avisar("Remarcação tratada.");
    setForm({ acao: "REMARCAR", nova_data_hora: "", novo_profissional_id: "", incluir_fila_espera: false, observacao: "" });
    onSalvo();
  });
  const ag = remarcacao?.agendamento;
  const compat = profissionais.filter((p) => !ag || p.especialidades.some((e) => e.id === ag.especialidade.id));

  return (
    <Modal
      aberto={remarcacao !== null}
      titulo="Tratar remarcação"
      onFechar={onFechar}
      rodape={
        <>
          <Botao variante="secundario" onClick={onFechar}>
            Fechar
          </Botao>
          <Botao type="submit" form="form-remarcacao" carregando={salvar.executando}>
            Confirmar
          </Botao>
        </>
      }
    >
      {ag && (
        <>
          {salvar.erro && <Alerta onFechar={salvar.limparErro}>{salvar.erro}</Alerta>}
          <dl className="mb-4 grid grid-cols-2 gap-3 rounded-lg bg-slate-50 p-3">
            <ItemDefinicao termo="Paciente">{ag.paciente.nome}</ItemDefinicao>
            <ItemDefinicao termo="Consulta atual">{dataHora(ag.data_hora)}</ItemDefinicao>
            <ItemDefinicao termo="Especialidade">{ag.especialidade.nome}</ItemDefinicao>
            <ItemDefinicao termo="Profissional">{ag.profissional.nome}</ItemDefinicao>
          </dl>
          <form
            id="form-remarcacao"
            className="space-y-4"
            onSubmit={(e) => {
              e.preventDefault();
              void salvar.executar();
            }}
          >
            <Selecao
              rotulo="Decisão"
              value={form.acao}
              onChange={(e) => setForm({ ...form, acao: e.target.value })}
              opcoes={[
                { value: "REMARCAR", label: "Remarcar para nova data" },
                { value: "MANTER", label: "Manter a consulta atual" },
                { value: "CANCELAR", label: "Cancelar a consulta" },
              ]}
            />
            {form.acao === "REMARCAR" && (
              <>
                <Entrada rotulo="Nova data e hora" type="datetime-local" required value={form.nova_data_hora} onChange={(e) => setForm({ ...form, nova_data_hora: e.target.value })} />
                <Selecao
                  rotulo="Profissional"
                  vazio="Mesmo profissional"
                  value={form.novo_profissional_id}
                  onChange={(e) => setForm({ ...form, novo_profissional_id: e.target.value })}
                  opcoes={compat.map((p) => ({ value: p.id, label: p.nome }))}
                />
              </>
            )}
            {form.acao === "CANCELAR" && (
              <Caixa
                rotulo="Incluir paciente na fila de espera"
                checked={form.incluir_fila_espera}
                onChange={(e) => setForm({ ...form, incluir_fila_espera: e.target.checked })}
              />
            )}
            <AreaTexto rotulo="Observação" maxLength={300} value={form.observacao} onChange={(e) => setForm({ ...form, observacao: e.target.value })} />
          </form>
        </>
      )}
    </Modal>
  );
}
