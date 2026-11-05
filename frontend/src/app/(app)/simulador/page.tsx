"use client";

import { useEffect, useState } from "react";
import { useAcao, useConsulta } from "@/hooks/useApi";
import { P } from "@/lib/permissoes";
import { api } from "@/lib/api";
import { dataHora, telefone } from "@/lib/formato";
import { ExigePermissao } from "@/components/AppShell";
import { Alerta, Botao, CabecalhoPagina, Caixa, Cartao, Entrada, Selo } from "@/components/ui";
import { useAvisos } from "@/components/ui/Aviso";

interface Mensagem {
  id_externo: string;
  data_hora: string;
  destino: string;
  tipo: string;
  texto: string;
  identificador: string | null;
  opcoes: string[];
}

const TAREFAS = [
  { nome: "lembretes", rotulo: "Enviar lembretes", ajuda: "Gera lembretes para consultas dentro da antecedência configurada." },
  { nome: "outbox", rotulo: "Processar fila de envio", ajuda: "Envia as mensagens pendentes (outbox)." },
  { nome: "expirar-respostas", rotulo: "Expirar respostas", ajuda: "Marca como sem resposta e libera vagas." },
  { nome: "expirar-ofertas", rotulo: "Expirar ofertas", ajuda: "Libera reservas vencidas e reoferta." },
  { nome: "retencao", rotulo: "Retenção LGPD", ajuda: "Executa eliminação/anonimização." },
  { nome: "ciclo", rotulo: "Ciclo completo", ajuda: "Executa todas as tarefas em sequência." },
];

export default function SimuladorPage() {
  return (
    <ExigePermissao permissao={P.TAREFAS_EXECUTAR}>
      <Conteudo />
    </ExigePermissao>
  );
}

function Conteudo() {
  const avisar = useAvisos();
  const [filtroTel, setFiltroTel] = useState("");
  const [auto, setAuto] = useState(true);
  const caixa = useConsulta<Mensagem[]>("/simulador/mensagens", { telefone: filtroTel, limite: 50 });
  const recarregarCaixa = caixa.recarregar;
  const [ultimo, setUltimo] = useState<unknown>(null);

  useEffect(() => {
    if (!auto) return;
    const t = setInterval(() => void recarregarCaixa(), 5000);
    return () => clearInterval(t);
  }, [auto, recarregarCaixa]);

  const tarefa = useAcao(async (nome: string) => {
    const { data } = await api.post(`/tarefas/${nome}`);
    setUltimo(data);
    avisar(`Tarefa "${nome}" executada.`);
    void caixa.recarregar();
  });

  const responder = useAcao(async (m: Mensagem, resposta: string) => {
    const { data } = await api.post("/simulador/responder", { telefone: m.destino, identificador: m.identificador, resposta });
    setUltimo(data);
    avisar(`Resposta "${resposta}" enviada como o paciente.`);
    void caixa.recarregar();
  });

  return (
    <>
      <CabecalhoPagina
        titulo="Simulador de mensagens"
        descricao="Ambiente de desenvolvimento: veja as mensagens que o sistema enviou e responda como se fosse o paciente. Também permite executar as tarefas agendadas na hora."
      />
      {(caixa.erro || tarefa.erro || responder.erro) && (
        <Alerta onFechar={() => (tarefa.limparErro(), responder.limparErro())}>{caixa.erro ?? tarefa.erro ?? responder.erro}</Alerta>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6">
          <Cartao titulo="Tarefas agendadas">
            <ul className="space-y-3">
              {TAREFAS.map((t) => (
                <li key={t.nome} className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium text-slate-800">{t.rotulo}</p>
                    <p className="text-xs text-slate-500">{t.ajuda}</p>
                  </div>
                  <Botao variante="secundario" tamanho="sm" carregando={tarefa.executando} onClick={() => tarefa.executar(t.nome)}>
                    Executar
                  </Botao>
                </li>
              ))}
            </ul>
          </Cartao>
          {ultimo !== null && (
            <Cartao titulo="Último resultado">
              <pre className="max-h-64 overflow-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-100">{JSON.stringify(ultimo, null, 2)}</pre>
            </Cartao>
          )}
        </div>

        <Cartao
          titulo="Caixa de saída (WhatsApp simulado)"
          className="lg:col-span-2"
          acoes={
            <div className="flex items-center gap-3">
              <Caixa rotulo="Atualizar a cada 5s" checked={auto} onChange={(e) => setAuto(e.target.checked)} />
              <Botao variante="secundario" tamanho="sm" onClick={() => caixa.recarregar()}>
                Atualizar
              </Botao>
            </div>
          }
        >
          <Entrada rotulo="Filtrar por telefone" placeholder="Últimos dígitos" value={filtroTel} onChange={(e) => setFiltroTel(e.target.value)} className="mb-4 max-w-xs" />
          {caixa.dados?.length === 0 && <p className="py-8 text-center text-sm text-slate-500">Nenhuma mensagem enviada ainda. Execute “Enviar lembretes” e depois “Processar fila de envio”.</p>}
          <ul className="space-y-3">
            {caixa.dados?.map((m) => (
              <li key={m.id_externo} className="rounded-xl border border-slate-200 bg-emerald-50/40 p-3">
                <div className="mb-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                  <span className="font-medium text-slate-700">Para {telefone(m.destino)}</span>
                  <Selo cor={m.tipo.toLowerCase().includes("oferta") ? "roxo" : "azul"}>{m.tipo}</Selo>
                  <span>{dataHora(m.data_hora)}</span>
                  {m.identificador && <code className="rounded bg-slate-100 px-1">{m.identificador}</code>}
                </div>
                <p className="whitespace-pre-line text-sm text-slate-800">{m.texto}</p>
                {m.opcoes.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    <span className="self-center text-xs text-slate-500">Responder como paciente:</span>
                    {m.opcoes.map((o) => (
                      <Botao key={o} variante="secundario" tamanho="sm" carregando={responder.executando} onClick={() => responder.executar(m, o)}>
                        {o}
                      </Botao>
                    ))}
                  </div>
                )}
              </li>
            ))}
          </ul>
        </Cartao>
      </div>
    </>
  );
}
