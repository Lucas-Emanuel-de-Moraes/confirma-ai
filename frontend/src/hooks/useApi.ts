"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, mensagemErro } from "@/lib/api";

interface EstadoConsulta<T> {
  dados: T | null;
  carregando: boolean;
  erro: string | null;
  recarregar: () => void;
}

interface Resultado<T> {
  url: string | null;
  chave: string | null;
  dados: T | null;
  erro: string | null;
}

/**
 * GET com axios: refaz a busca quando `url` ou `params` mudam.
 * Passe `url = null` para não buscar (ex.: sem permissão ou sem id selecionado).
 * Ao trocar só os filtros, os dados anteriores continuam visíveis até a nova resposta.
 */
export function useConsulta<T>(url: string | null, params?: Record<string, unknown>): EstadoConsulta<T> {
  const chaveParams = JSON.stringify(params ?? {});
  const [versao, setVersao] = useState(0);
  const chave = url === null ? null : `${url}?${chaveParams}#${versao}`;
  const [res, setRes] = useState<Resultado<T>>({ url: null, chave: null, dados: null, erro: null });

  useEffect(() => {
    if (url === null || chave === null) return;
    let ativo = true;
    api
      .get<T>(url, { params: JSON.parse(chaveParams) })
      .then((r) => ativo && setRes({ url, chave, dados: r.data, erro: null }))
      .catch((e) => ativo && setRes((s) => ({ url, chave, dados: s.url === url ? s.dados : null, erro: mensagemErro(e) })));
    return () => {
      ativo = false;
    };
  }, [url, chave, chaveParams]);

  const recarregar = useCallback(() => setVersao((v) => v + 1), []);
  const mesmaUrl = res.url === url;

  return {
    dados: mesmaUrl ? res.dados : null,
    carregando: chave !== null && res.chave !== chave,
    erro: mesmaUrl && res.chave === chave ? res.erro : null,
    recarregar,
  };
}

interface EstadoAcao<A extends unknown[], R> {
  executar: (...args: A) => Promise<R | undefined>;
  executando: boolean;
  erro: string | null;
  limparErro: () => void;
}

/** Envolve uma chamada de escrita (POST/PUT/PATCH/DELETE) com estado de envio e erro. */
export function useAcao<A extends unknown[], R>(fn: (...args: A) => Promise<R>): EstadoAcao<A, R> {
  const [executando, setExecutando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const ref = useRef(fn);
  useEffect(() => {
    ref.current = fn;
  });

  const executar = useCallback(async (...args: A) => {
    setExecutando(true);
    setErro(null);
    try {
      return await ref.current(...args);
    } catch (e) {
      setErro(mensagemErro(e));
      return undefined;
    } finally {
      setExecutando(false);
    }
  }, []);

  const limparErro = useCallback(() => setErro(null), []);
  return { executar, executando, erro, limparErro };
}

/** Atraso para campos de busca (evita uma requisição por tecla). */
export function useDebounce<T>(valor: T, ms = 350): T {
  const [v, setV] = useState(valor);
  useEffect(() => {
    const t = setTimeout(() => setV(valor), ms);
    return () => clearTimeout(t);
  }, [valor, ms]);
  return v;
}
