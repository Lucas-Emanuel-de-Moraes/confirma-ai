"use client";

import { useState } from "react";
import { useConsulta, useDebounce } from "@/hooks/useApi";
import { telefone } from "@/lib/formato";
import type { Pagina, Paciente, Referencia } from "@/lib/types";
import { Entrada } from "./ui";

/** Campo de busca de paciente ativo (por nome ou telefone) com lista de resultados. */
export function SeletorPaciente({ valor, onChange, rotulo = "Paciente" }: { valor: Referencia | null; onChange: (p: Referencia | null) => void; rotulo?: string }) {
  const [busca, setBusca] = useState("");
  const buscaD = useDebounce(busca);
  const { dados, carregando } = useConsulta<Pagina<Paciente>>(!valor && buscaD.length >= 2 ? "/pacientes" : null, { busca: buscaD, ativo: true, size: 8 });

  if (valor) {
    return (
      <div>
        <p className="mb-1 text-sm font-medium text-slate-700">{rotulo}</p>
        <div className="flex items-center justify-between rounded-lg border border-marca-200 bg-marca-50 px-3 py-2 text-sm">
          <span className="font-medium text-marca-900">{valor.nome}</span>
          <button type="button" className="text-xs text-marca-700 hover:underline" onClick={() => onChange(null)}>
            Trocar
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <Entrada rotulo={rotulo} required placeholder="Digite ao menos 2 letras do nome ou telefone" value={busca} onChange={(e) => setBusca(e.target.value)} />
      {buscaD.length >= 2 && (
        <ul className="mt-1 max-h-48 overflow-y-auto rounded-lg border border-slate-200 bg-white text-sm shadow-sm" role="listbox">
          {carregando && <li className="px-3 py-2 text-slate-500">Buscando…</li>}
          {!carregando && dados?.itens.length === 0 && <li className="px-3 py-2 text-slate-500">Nenhum paciente ativo encontrado.</li>}
          {dados?.itens.map((p) => (
            <li key={p.id}>
              <button
                type="button"
                role="option"
                aria-selected={false}
                className="flex w-full justify-between px-3 py-2 text-left hover:bg-marca-50"
                onClick={() => {
                  onChange({ id: p.id, nome: p.nome });
                  setBusca("");
                }}
              >
                <span>{p.nome}</span>
                <span className="text-slate-500">{telefone(p.telefone)}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
