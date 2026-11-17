"use client";

import { useCallback, useEffect, useState } from "react";
import { listarTodos } from "@/lib/api";
import type { Especialidade, Profissional, Unidade } from "@/lib/types";

interface Dados {
  unidades: Unidade[];
  especialidades: Especialidade[];
  profissionais: Profissional[];
}

/** Carrega unidades, especialidades e profissionais ativos para filtros e selects. */
export function useCadastros() {
  const [dados, setDados] = useState<Dados>({ unidades: [], especialidades: [], profissionais: [] });
  const [carregando, setCarregando] = useState(true);
  const [versao, setVersao] = useState(0);

  useEffect(() => {
    let ativo = true;
    Promise.all([
      listarTodos<Unidade>("/unidades", { ativo: true }),
      listarTodos<Especialidade>("/especialidades", { ativo: true }),
      listarTodos<Profissional>("/profissionais", { ativo: true }),
    ])
      .then(([unidades, especialidades, profissionais]) => ativo && setDados({ unidades, especialidades, profissionais }))
      .catch(() => {
        /* sem permissão de estrutura: selects ficam vazios */
      })
      .finally(() => ativo && setCarregando(false));
    return () => {
      ativo = false;
    };
  }, [versao]);

  const recarregar = useCallback(() => setVersao((v) => v + 1), []);
  const { unidades, especialidades, profissionais } = dados;

  const nome = (lista: { id: number; nome: string }[], id: number | null | undefined) => lista.find((x) => x.id === id)?.nome ?? (id ? `#${id}` : "—");

  return {
    unidades,
    especialidades,
    profissionais,
    carregando,
    recarregar,
    nomeUnidade: (id: number | null | undefined) => nome(unidades, id),
    nomeEspecialidade: (id: number | null | undefined) => nome(especialidades, id),
    nomeProfissional: (id: number | null | undefined) => nome(profissionais, id),
  };
}
