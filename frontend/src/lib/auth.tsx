"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { authApi, definirAoExpirarSessao, tokenStorage } from "./api";
import { temPermissao, type Permissao } from "./permissoes";
import type { Usuario } from "./types";

interface ContextoAuth {
  usuario: Usuario | null;
  carregando: boolean;
  entrar: (login: string, senha: string) => Promise<void>;
  sair: () => void;
  pode: (permissao: Permissao) => boolean;
}

const Ctx = createContext<ContextoAuth | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [carregando, setCarregando] = useState(true);

  const sair = useCallback(() => {
    tokenStorage.limpar();
    setUsuario(null);
    router.replace("/login");
  }, [router]);

  useEffect(() => {
    definirAoExpirarSessao(() => {
      setUsuario(null);
      router.replace("/login?expirou=1");
    });
    return () => definirAoExpirarSessao(null);
  }, [router]);

  useEffect(() => {
    const sessao = tokenStorage.obter() ? authApi.me() : Promise.resolve(null);
    sessao
      .then(setUsuario)
      .catch(() => tokenStorage.limpar())
      .finally(() => setCarregando(false));
  }, []);

  const entrar = useCallback(async (login: string, senha: string) => {
    const token = await authApi.login(login, senha);
    tokenStorage.salvar(token.access_token);
    setUsuario(await authApi.me());
  }, []);

  const valor = useMemo<ContextoAuth>(
    () => ({ usuario, carregando, entrar, sair, pode: (p) => temPermissao(usuario?.perfis, p) }),
    [usuario, carregando, entrar, sair],
  );

  return <Ctx.Provider value={valor}>{children}</Ctx.Provider>;
}

export function useAuth(): ContextoAuth {
  const c = useContext(Ctx);
  if (!c) throw new Error("useAuth precisa estar dentro de <AuthProvider>");
  return c;
}
