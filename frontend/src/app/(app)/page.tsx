"use client";

import Link from "next/link";
import { useConsulta } from "@/hooks/useApi";
import { useAuth } from "@/lib/auth";
import { P } from "@/lib/permissoes";
import { API_URL } from "@/lib/api";
import { dataHora, hora } from "@/lib/formato";
import { useHoje } from "@/hooks/useHoje";
import type { Agendamento, Health, Indicadores, Oferta, Pagina, Remarcacao, Vaga } from "@/lib/types";
import { Alerta, CabecalhoPagina, Cartao, Selo } from "@/components/ui";
import { Tabela } from "@/components/ui/Tabela";
import { CartaoNumero, Taxas } from "@/components/Indicadores";
import { SeloAgendamento, SeloOferta } from "@/components/Status";
import { useEffect, useState } from "react";
import axios from "axios";

export default function PainelPage() {
  const { usuario, pode } = useAuth();
  const hoje = useHoje();
  const agenda = useConsulta<Pagina<Agendamento>>(hoje && pode(P.AGENDA_LER) ? "/agendamentos" : null, { data: hoje, size: 50 });
  const remarcacoes = useConsulta<Pagina<Remarcacao>>(pode(P.AGENDA_LER) ? "/remarcacoes" : null, { status: "PENDENTE", size: 1 });
  const vagas = useConsulta<Pagina<Vaga>>(pode(P.OFERTAS_LER) ? "/vagas" : null, { status: "EM_OFERTA", size: 1 });
  const ofertas = useConsulta<Pagina<Oferta>>(pode(P.OFERTAS_LER) ? "/ofertas" : null, { status: "RESERVADA", size: 5 });
  const indicadores = useConsulta<Indicadores>(pode(P.INDICADORES_LER) ? "/indicadores" : null);
  const [saude, setSaude] = useState<Health | null>(null);

  useEffect(() => {
    // O health check fica fora do prefixo /api/v1
    axios
      .get<Health>(API_URL.replace(/\/v1\/?$/, "") + "/health", { validateStatus: () => true })
      .then((r) => setSaude(r.data))
      .catch(() => setSaude(null));
  }, []);

  const pendentesResposta = agenda.dados?.itens.filter((a) => a.status === "AGUARDANDO_RESPOSTA").length ?? 0;
  const confirmadosHoje = agenda.dados?.itens.filter((a) => a.status === "CONFIRMADO").length ?? 0;

  return (
    <>
      <CabecalhoPagina
        titulo={`Olá, ${usuario?.nome.split(" ")[0]}`}
        descricao="Resumo do dia: consultas, confirmações pendentes e vagas sendo recuperadas."
        acoes={
          saude && (
            <Selo cor={saude.status === "ok" ? "verde" : "vermelho"} title={`Banco: ${saude.banco} · Agendador: ${saude.agendador ? "ativo" : "parado"}`}>
              API {saude.status === "ok" ? "operacional" : "degradada"} · mensageria: {saude.mensageria}
            </Selo>
          )
        }
      />

      {agenda.erro && <Alerta>{agenda.erro}</Alerta>}

      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        {pode(P.AGENDA_LER) && <CartaoNumero titulo="Consultas hoje" valor={agenda.dados?.total ?? "—"} detalhe={`${confirmadosHoje} confirmada(s)`} />}
        {pode(P.AGENDA_LER) && <CartaoNumero titulo="Aguardando resposta" valor={pendentesResposta} detalhe="Lembretes enviados hoje" />}
        {pode(P.AGENDA_LER) && <CartaoNumero titulo="Remarcações pendentes" valor={remarcacoes.dados?.total ?? "—"} detalhe="Precisam de ação da recepção" />}
        {pode(P.OFERTAS_LER) && <CartaoNumero titulo="Vagas em oferta" valor={vagas.dados?.total ?? "—"} detalhe="Reservas temporárias ativas" />}
      </div>

      {indicadores.dados && (
        <div className="mb-6">
          <h2 className="mb-2 text-sm font-semibold text-slate-700">
            Últimos 60 dias{" "}
            <Link href="/indicadores" className="font-normal text-marca-700 hover:underline">
              ver indicadores →
            </Link>
          </h2>
          <Taxas dados={indicadores.dados} />
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        {pode(P.AGENDA_LER) && (
          <Cartao
            titulo="Agenda de hoje"
            className="lg:col-span-2"
            acoes={
              <Link href="/agenda" className="text-sm text-marca-700 hover:underline">
                Abrir agenda
              </Link>
            }
          >
            <Tabela
              itens={agenda.dados?.itens}
              carregando={agenda.carregando}
              chave={(a) => a.id}
              vazio="Nenhuma consulta para hoje."
              colunas={[
                { titulo: "Hora", render: (a) => <span className="font-medium tabular-nums">{hora(a.data_hora)}</span> },
                { titulo: "Paciente", render: (a) => a.paciente.nome },
                { titulo: "Profissional", render: (a) => a.profissional.nome },
                { titulo: "Status", render: (a) => <SeloAgendamento status={a.status} descricao={a.status_descricao} /> },
              ]}
            />
          </Cartao>
        )}
        {pode(P.OFERTAS_LER) && (
          <Cartao
            titulo="Ofertas aguardando resposta"
            acoes={
              <Link href="/vagas" className="text-sm text-marca-700 hover:underline">
                Ver todas
              </Link>
            }
          >
            <ul className="divide-y divide-slate-100">
              {ofertas.dados?.itens.length === 0 && <li className="py-6 text-center text-sm text-slate-500">Nenhuma oferta ativa.</li>}
              {ofertas.dados?.itens.map((o) => (
                <li key={o.id} className="py-2.5 text-sm">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium text-slate-800">{o.paciente.nome}</span>
                    <SeloOferta status={o.status} />
                  </div>
                  <p className="text-xs text-slate-500">
                    Vaga {dataHora(o.vaga_data_hora)} · prazo {hora(o.prazo_resposta)}
                  </p>
                </li>
              ))}
            </ul>
          </Cartao>
        )}
      </div>
    </>
  );
}
