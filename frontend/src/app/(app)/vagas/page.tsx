"use client";

import { useState } from "react";
import { useAcao, useConsulta } from "@/hooks/useApi";
import { useCadastros } from "@/hooks/useCadastros";
import { useAuth } from "@/lib/auth";
import { P } from "@/lib/permissoes";
import { api, lerErro } from "@/lib/api";
import { dataHora, opcoes } from "@/lib/formato";
import type { Oferta, Pagina, Vaga } from "@/lib/types";
import { ExigePermissao } from "@/components/AppShell";
import { Abas, Alerta, BarraFiltros, Botao, CabecalhoPagina, Caixa, Cartao, Entrada, Selecao } from "@/components/ui";
import { Modal } from "@/components/ui/Modal";
import { Paginacao, Tabela } from "@/components/ui/Tabela";
import { useAvisos } from "@/components/ui/Aviso";
import { SeloOferta, SeloVaga } from "@/components/Status";

export default function VagasPage() {
  return (
    <ExigePermissao permissao={P.OFERTAS_LER}>
      <Conteudo />
    </ExigePermissao>
  );
}

function Conteudo() {
  const [aba, setAba] = useState<"vagas" | "ofertas">("vagas");
  const [vagaFiltro, setVagaFiltro] = useState<number | null>(null);
  return (
    <>
      <CabecalhoPagina
        titulo="Vagas e ofertas"
        descricao="Vagas liberadas por cancelamento ou não confirmação e ofertas de encaixe com reserva temporária (UC05–UC07)."
      />
      <Abas
        abas={[
          { id: "vagas", rotulo: "Vagas liberadas" },
          { id: "ofertas", rotulo: "Ofertas de encaixe" },
        ]}
        ativa={aba}
        onChange={(a) => {
          setAba(a);
          if (a === "vagas") setVagaFiltro(null);
        }}
      />
      {aba === "vagas" ? (
        <PainelVagas
          onVerOfertas={(id) => {
            setVagaFiltro(id);
            setAba("ofertas");
          }}
        />
      ) : (
        <PainelOfertas vagaId={vagaFiltro} onLimparVaga={() => setVagaFiltro(null)} />
      )}
    </>
  );
}

function PainelVagas({ onVerOfertas }: { onVerOfertas: (vagaId: number) => void }) {
  const { pode } = useAuth();
  const avisar = useAvisos();
  const cad = useCadastros();
  const [f, setF] = useState({ status: "", unidade_id: "" });
  const [page, setPage] = useState(1);
  const lista = useConsulta<Pagina<Vaga>>("/vagas", { ...f, page, size: 20 });
  const ofertar = useAcao(async (v: Vaga) => {
    const { data } = await api.post<Vaga>(`/vagas/${v.id}/ofertar`);
    avisar(data.status === "EM_OFERTA" ? "Oferta enviada ao próximo paciente elegível." : "Nenhum paciente elegível na fila para esta vaga.", data.status === "EM_OFERTA" ? "sucesso" : "info");
    void lista.recarregar();
  });

  return (
    <>
      <BarraFiltros>
        <Selecao
          rotulo="Status"
          vazio="Todos"
          value={f.status}
          onChange={(e) => {
            setF({ ...f, status: e.target.value });
            setPage(1);
          }}
          opcoes={opcoes("statusVaga")}
        />
        <Selecao
          rotulo="Unidade"
          vazio="Todas"
          value={f.unidade_id}
          onChange={(e) => {
            setF({ ...f, unidade_id: e.target.value });
            setPage(1);
          }}
          opcoes={cad.unidades.map((u) => ({ value: u.id, label: u.nome }))}
        />
      </BarraFiltros>
      {(lista.erro || ofertar.erro) && <Alerta onFechar={ofertar.limparErro}>{lista.erro ?? ofertar.erro}</Alerta>}
      <Cartao>
        <Tabela
          itens={lista.dados?.itens}
          carregando={lista.carregando}
          chave={(v) => v.id}
          vazio="Nenhuma vaga liberada."
          colunas={[
            { titulo: "Horário da vaga", render: (v) => <span className="font-medium tabular-nums">{dataHora(v.data_hora)}</span> },
            { titulo: "Especialidade", render: (v) => cad.nomeEspecialidade(v.especialidade_id) },
            { titulo: "Profissional", render: (v) => cad.nomeProfissional(v.profissional_id) },
            { titulo: "Unidade", render: (v) => cad.nomeUnidade(v.unidade_id) },
            { titulo: "Motivo", render: (v) => <span className="text-xs">{v.motivo_liberacao}</span> },
            { titulo: "Liberada em", render: (v) => dataHora(v.data_liberacao) },
            { titulo: "Status", render: (v) => <SeloVaga status={v.status} /> },
            {
              titulo: "",
              className: "text-right",
              render: (v) => (
                <div className="flex justify-end gap-1">
                  <Botao variante="fantasma" tamanho="sm" onClick={() => onVerOfertas(v.id)}>
                    Ofertas
                  </Botao>
                  {pode(P.OFERTAS_GERENCIAR) && ["DISPONIVEL", "SEM_ELEGIVEIS"].includes(v.status) && (
                    <Botao tamanho="sm" carregando={ofertar.executando} onClick={() => ofertar.executar(v)}>
                      Ofertar
                    </Botao>
                  )}
                </div>
              ),
            },
          ]}
        />
        {lista.dados && <Paginacao {...lista.dados} onPage={setPage} />}
      </Cartao>
    </>
  );
}

function PainelOfertas({ vagaId, onLimparVaga }: { vagaId: number | null; onLimparVaga: () => void }) {
  const { pode } = useAuth();
  const avisar = useAvisos();
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const lista = useConsulta<Pagina<Oferta>>("/ofertas", { status, vaga_id: vagaId, page, size: 20 });
  const [cancelar, setCancelar] = useState<Oferta | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const acao = useAcao(async (o: Oferta, tipo: "aceitar" | "recusar") => {
    try {
      await api.post(`/ofertas/${o.id}/${tipo}`);
      avisar(tipo === "aceitar" ? "Aceite registrado. O agendamento foi criado." : "Recusa registrada. A vaga será reofertada.");
    } catch (e) {
      const err = lerErro(e);
      // 409: outra pessoa já ocupou a vaga (aceite atômico, RF17)
      setErro(err.mensagem);
    }
    void lista.recarregar();
  });
  const gerenciar = pode(P.OFERTAS_GERENCIAR);

  return (
    <>
      <BarraFiltros>
        <Selecao
          rotulo="Status"
          vazio="Todos"
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setPage(1);
          }}
          opcoes={opcoes("statusOferta")}
        />
        {vagaId && (
          <div className="flex items-end">
            <Botao variante="secundario" onClick={onLimparVaga}>
              Vaga #{vagaId} · limpar filtro ×
            </Botao>
          </div>
        )}
      </BarraFiltros>
      {(lista.erro || erro) && <Alerta onFechar={() => setErro(null)}>{lista.erro ?? erro}</Alerta>}
      <Cartao>
        <Tabela
          itens={lista.dados?.itens}
          carregando={lista.carregando}
          chave={(o) => o.id}
          vazio="Nenhuma oferta."
          colunas={[
            { titulo: "Paciente", render: (o) => <span className="font-medium">{o.paciente.nome}</span> },
            { titulo: "Vaga", render: (o) => `${dataHora(o.vaga_data_hora)} (#${o.vaga_id})` },
            { titulo: "Prazo de resposta", render: (o) => dataHora(o.prazo_resposta) },
            { titulo: "Critério", render: (o) => <span className="text-xs text-slate-600">{o.criterio_selecao ?? "—"}</span> },
            {
              titulo: "Status",
              render: (o) => (
                <div>
                  <SeloOferta status={o.status} />
                  {o.motivo && <p className="mt-0.5 text-xs text-slate-500">{o.motivo}</p>}
                </div>
              ),
            },
            {
              titulo: "",
              className: "text-right",
              render: (o) =>
                gerenciar && o.status === "RESERVADA" ? (
                  <div className="flex justify-end gap-1">
                    <Botao tamanho="sm" carregando={acao.executando} onClick={() => acao.executar(o, "aceitar")} title="Paciente aceitou por telefone">
                      Aceitar
                    </Botao>
                    <Botao variante="secundario" tamanho="sm" carregando={acao.executando} onClick={() => acao.executar(o, "recusar")}>
                      Recusar
                    </Botao>
                    <Botao variante="fantasma" tamanho="sm" onClick={() => setCancelar(o)}>
                      Cancelar
                    </Botao>
                  </div>
                ) : null,
            },
          ]}
        />
        {lista.dados && <Paginacao {...lista.dados} onPage={setPage} />}
      </Cartao>
      <CancelarOferta
        oferta={cancelar}
        onFechar={() => setCancelar(null)}
        onSalvo={() => {
          setCancelar(null);
          void lista.recarregar();
        }}
      />
    </>
  );
}

function CancelarOferta({ oferta, onFechar, onSalvo }: { oferta: Oferta | null; onFechar: () => void; onSalvo: () => void }) {
  const avisar = useAvisos();
  const [motivo, setMotivo] = useState("");
  const [reofertar, setReofertar] = useState(true);
  const salvar = useAcao(async () => {
    if (!oferta) return;
    await api.post(`/ofertas/${oferta.id}/cancelar`, { motivo, reofertar });
    avisar("Reserva cancelada.");
    setMotivo("");
    onSalvo();
  });
  return (
    <Modal
      aberto={oferta !== null}
      titulo="Cancelar reserva"
      onFechar={onFechar}
      rodape={
        <>
          <Botao variante="secundario" onClick={onFechar}>
            Voltar
          </Botao>
          <Botao variante="perigo" type="submit" form="form-cancelar-oferta" carregando={salvar.executando}>
            Cancelar reserva
          </Botao>
        </>
      }
    >
      {salvar.erro && <Alerta onFechar={salvar.limparErro}>{salvar.erro}</Alerta>}
      <form
        id="form-cancelar-oferta"
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          void salvar.executar();
        }}
      >
        <Entrada rotulo="Motivo" required value={motivo} onChange={(e) => setMotivo(e.target.value)} />
        <Caixa rotulo="Ofertar ao próximo elegível da fila" checked={reofertar} onChange={(e) => setReofertar(e.target.checked)} />
      </form>
    </Modal>
  );
}
