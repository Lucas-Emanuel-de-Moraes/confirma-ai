"use client";

import { useState } from "react";
import { useConsulta } from "@/hooks/useApi";
import { useCadastros } from "@/hooks/useCadastros";
import { P } from "@/lib/permissoes";
import { data, somarDias } from "@/lib/formato";
import { useHoje } from "@/hooks/useHoje";
import type { Indicadores } from "@/lib/types";
import { ExigePermissao } from "@/components/AppShell";
import { Alerta, BarraFiltros, CabecalhoPagina, Cartao, Carregando, Entrada, Selecao } from "@/components/ui";
import { Barras, CartaoNumero, Taxas } from "@/components/Indicadores";

export default function IndicadoresPage() {
  return (
    <ExigePermissao permissao={P.INDICADORES_LER}>
      <ComData />
    </ExigePermissao>
  );
}

/** Só monta a página quando a data do navegador está disponível (não no pré-render). */
function ComData() {
  const hoje = useHoje();
  return hoje ? <Conteudo hoje={hoje} /> : null;
}

function Conteudo({ hoje }: { hoje: string }) {
  const { unidades, especialidades, profissionais } = useCadastros();
  const [f, setF] = useState({ inicio: somarDias(hoje, -30), fim: somarDias(hoje, 30), unidade_id: "", especialidade_id: "", profissional_id: "" });
  const { dados, carregando, erro } = useConsulta<Indicadores>("/indicadores", f);
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setF({ ...f, [k]: e.target.value });

  return (
    <>
      <CabecalhoPagina titulo="Indicadores" descricao="Absenteísmo, confirmação e recuperação de vagas no período (RF19 / UC09)." />
      <BarraFiltros>
        <Entrada rotulo="De" type="date" value={f.inicio} onChange={set("inicio")} />
        <Entrada rotulo="Até" type="date" value={f.fim} onChange={set("fim")} />
        <Selecao rotulo="Unidade" vazio="Todas" value={f.unidade_id} onChange={set("unidade_id")} opcoes={unidades.map((u) => ({ value: u.id, label: u.nome }))} />
        <Selecao rotulo="Especialidade" vazio="Todas" value={f.especialidade_id} onChange={set("especialidade_id")} opcoes={especialidades.map((e) => ({ value: e.id, label: e.nome }))} />
        <Selecao rotulo="Profissional" vazio="Todos" value={f.profissional_id} onChange={set("profissional_id")} opcoes={profissionais.map((p) => ({ value: p.id, label: p.nome }))} />
      </BarraFiltros>

      {erro && <Alerta>{erro}</Alerta>}
      {carregando && !dados && <Carregando />}
      {dados && (
        <div className="space-y-6">
          <p className="text-sm text-slate-500">
            Período considerado: {data(dados.periodo.inicio)} a {data(dados.periodo.fim)}
          </p>
          <Taxas dados={dados} />

          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <CartaoNumero titulo="Agendamentos" valor={dados.agendamentos.total} />
            <CartaoNumero titulo="Confirmados" valor={dados.agendamentos.confirmados} />
            <CartaoNumero titulo="Sem resposta" valor={dados.agendamentos.nao_respondidos} />
            <CartaoNumero titulo="Faltas" valor={dados.agendamentos.faltas} />
            <CartaoNumero titulo="Vagas liberadas" valor={dados.vagas.liberadas} />
            <CartaoNumero titulo="Vagas recuperadas" valor={dados.vagas.recuperadas} />
            <CartaoNumero titulo="Sem elegíveis" valor={dados.vagas.sem_elegiveis} />
            <CartaoNumero
              titulo="Tempo médio de recuperação"
              valor={dados.vagas.tempo_medio_recuperacao_min !== null ? `${dados.vagas.tempo_medio_recuperacao_min} min` : "—"}
            />
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <Cartao>
              <Barras titulo="Agendamentos por status" valores={dados.agendamentos.por_status} grupo="statusAgendamento" />
            </Cartao>
            <Cartao>
              <Barras titulo="Ofertas de encaixe por status" valores={dados.ofertas} grupo="statusOferta" />
            </Cartao>
          </div>
        </div>
      )}
    </>
  );
}
