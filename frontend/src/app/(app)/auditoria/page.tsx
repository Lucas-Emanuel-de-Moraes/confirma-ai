"use client";

import { useState } from "react";
import { useConsulta, useDebounce } from "@/hooks/useApi";
import { P } from "@/lib/permissoes";
import { dataHora } from "@/lib/formato";
import type { LogAuditoria, Pagina } from "@/lib/types";
import { ExigePermissao } from "@/components/AppShell";
import { Alerta, BarraFiltros, CabecalhoPagina, Cartao, Entrada } from "@/components/ui";
import { Modal } from "@/components/ui/Modal";
import { Paginacao, Tabela } from "@/components/ui/Tabela";

export default function AuditoriaPage() {
  return (
    <ExigePermissao permissao={P.AUDITORIA_LER}>
      <Conteudo />
    </ExigePermissao>
  );
}

function Conteudo() {
  const [f, setF] = useState({ entidade: "", entidade_id: "", acao: "", inicio: "", fim: "" });
  const [page, setPage] = useState(1);
  const fD = useDebounce(f);
  const lista = useConsulta<Pagina<LogAuditoria>>("/auditoria", {
    ...fD,
    inicio: fD.inicio ? `${fD.inicio}T00:00:00` : "",
    fim: fD.fim ? `${fD.fim}T23:59:59` : "",
    page,
    size: 30,
  });
  const [detalhe, setDetalhe] = useState<LogAuditoria | null>(null);
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => (setF({ ...f, [k]: e.target.value }), setPage(1));

  return (
    <>
      <CabecalhoPagina titulo="Auditoria" descricao="Eventos registrados com data, hora, origem e usuário (PB09)." />
      <BarraFiltros>
        <Entrada rotulo="Entidade" placeholder="ex.: agendamento" value={f.entidade} onChange={set("entidade")} />
        <Entrada rotulo="ID da entidade" value={f.entidade_id} onChange={set("entidade_id")} />
        <Entrada rotulo="Ação" placeholder="ex.: CRIAR" value={f.acao} onChange={set("acao")} />
        <div className="grid grid-cols-2 gap-2">
          <Entrada rotulo="De" type="date" value={f.inicio} onChange={set("inicio")} />
          <Entrada rotulo="Até" type="date" value={f.fim} onChange={set("fim")} />
        </div>
      </BarraFiltros>
      {lista.erro && <Alerta>{lista.erro}</Alerta>}
      <Cartao>
        <Tabela
          itens={lista.dados?.itens}
          carregando={lista.carregando}
          chave={(l) => l.id}
          onLinha={setDetalhe}
          colunas={[
            { titulo: "Data e hora", render: (l) => <span className="tabular-nums">{dataHora(l.data_hora)}</span> },
            { titulo: "Ação", render: (l) => <code className="text-xs">{l.acao}</code> },
            { titulo: "Entidade", render: (l) => `${l.entidade}${l.entidade_id ? ` #${l.entidade_id}` : ""}` },
            { titulo: "Origem", render: (l) => l.origem },
            { titulo: "Usuário", render: (l) => (l.usuario_id ? `#${l.usuario_id}` : "sistema") },
          ]}
        />
        {lista.dados && <Paginacao {...lista.dados} onPage={setPage} />}
      </Cartao>
      <Modal aberto={detalhe !== null} titulo={`Evento #${detalhe?.id ?? ""}`} onFechar={() => setDetalhe(null)} largura="lg">
        <pre className="max-h-[60vh] overflow-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-100">{JSON.stringify(detalhe, null, 2)}</pre>
      </Modal>
    </>
  );
}
