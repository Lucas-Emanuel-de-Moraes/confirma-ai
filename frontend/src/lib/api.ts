import axios, { AxiosError } from "axios";
import type { ErroApi, Pagina, Token, Usuario } from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
const CHAVE_TOKEN = "confirma-ai:token";

export const tokenStorage = {
  obter(): string | null {
    if (typeof window === "undefined") return null;
    try {
      return window.localStorage.getItem(CHAVE_TOKEN);
    } catch {
      return null;
    }
  },
  salvar(token: string) {
    try {
      window.localStorage.setItem(CHAVE_TOKEN, token);
    } catch {
      /* armazenamento indisponível */
    }
  },
  limpar() {
    try {
      window.localStorage.removeItem(CHAVE_TOKEN);
    } catch {
      /* armazenamento indisponível */
    }
  },
};

export const api = axios.create({
  baseURL: API_URL,
  timeout: 20000,
  // Listas (ex.: status=A&status=B) no formato que o FastAPI espera
  paramsSerializer: { indexes: null },
});

api.interceptors.request.use((config) => {
  const token = tokenStorage.obter();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  // Remove filtros vazios para não enviar "?busca=" ao back-end
  if (config.params) {
    config.params = Object.fromEntries(
      Object.entries(config.params).filter(([, v]) => v !== "" && v !== null && v !== undefined),
    );
  }
  return config;
});

/** Chamado quando a API devolve 401 (token expirado ou inválido). */
let aoExpirarSessao: (() => void) | null = null;
export function definirAoExpirarSessao(fn: (() => void) | null) {
  aoExpirarSessao = fn;
}

api.interceptors.response.use(
  (r) => r,
  (erro: AxiosError) => {
    const url = erro.config?.url ?? "";
    if (erro.response?.status === 401 && !url.includes("/auth/login")) {
      tokenStorage.limpar();
      aoExpirarSessao?.();
    }
    return Promise.reject(erro);
  },
);

/** Extrai a mensagem do formato padronizado { codigo, mensagem, campos }. */
export function lerErro(erro: unknown): ErroApi {
  if (axios.isAxiosError(erro)) {
    const corpo = erro.response?.data as Partial<ErroApi> | undefined;
    if (corpo && typeof corpo.mensagem === "string") {
      return { codigo: corpo.codigo ?? "ERRO", mensagem: corpo.mensagem, campos: corpo.campos ?? [] };
    }
    if (!erro.response) {
      return { codigo: "REDE", mensagem: "Não foi possível conectar à API. Verifique se o back-end está no ar.", campos: [] };
    }
    return { codigo: `HTTP_${erro.response.status}`, mensagem: "Erro inesperado na requisição.", campos: [] };
  }
  return { codigo: "ERRO", mensagem: erro instanceof Error ? erro.message : "Erro inesperado.", campos: [] };
}

export function mensagemErro(erro: unknown): string {
  const e = lerErro(erro);
  if (e.campos.length) {
    return `${e.mensagem} ${e.campos.map((c) => `${c.campo ? c.campo + ": " : ""}${c.erro}`).join("; ")}`;
  }
  return e.mensagem;
}

export const authApi = {
  async login(login: string, senha: string): Promise<Token> {
    const corpo = new URLSearchParams({ username: login, password: senha });
    const { data } = await api.post<Token>("/auth/login", corpo, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    return data;
  },
  async me(): Promise<Usuario> {
    const { data } = await api.get<Usuario>("/auth/me");
    return data;
  },
};

/** Busca todas as páginas de uma lista (útil para selects de cadastros pequenos). */
export async function listarTodos<T>(url: string, params: Record<string, unknown> = {}): Promise<T[]> {
  const itens: T[] = [];
  let page = 1;
  for (;;) {
    const { data } = await api.get<Pagina<T>>(url, { params: { ...params, page, size: 100 } });
    itens.push(...data.itens);
    if (itens.length >= data.total || data.itens.length === 0) return itens;
    page += 1;
  }
}
