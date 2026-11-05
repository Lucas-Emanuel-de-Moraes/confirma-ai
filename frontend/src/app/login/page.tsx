"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { mensagemErro } from "@/lib/api";
import { Alerta, Botao, Entrada } from "@/components/ui";

export default function LoginPage() {
  const { entrar, usuario, carregando } = useAuth();
  const router = useRouter();
  const [login, setLogin] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const expirou = useSyncExternalStore(
    () => () => {},
    () => window.location.search.includes("expirou"),
    () => false,
  );
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    if (!carregando && usuario) router.replace("/");
  }, [carregando, usuario, router]);

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    setErro(null);
    setEnviando(true);
    try {
      await entrar(login.trim(), senha);
      router.replace("/");
    } catch (err) {
      setErro(mensagemErro(err));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-gradient-to-br from-marca-900 to-marca-700 px-4">
      <div className="w-full max-w-sm rounded-2xl bg-white p-8 shadow-xl">
        <div className="mb-6 text-center">
          <span className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-marca-600 text-2xl font-bold text-white">✓</span>
          <h1 className="text-2xl font-bold text-slate-900">Confirma Aí</h1>
          <p className="mt-1 text-sm text-slate-500">Acesse com seu usuário individual</p>
        </div>

        {expirou && !erro && <Alerta tipo="aviso">Sua sessão expirou. Entre novamente.</Alerta>}
        {erro && <Alerta>{erro}</Alerta>}

        <form onSubmit={enviar} className="space-y-4">
          <Entrada rotulo="Usuário" autoComplete="username" required value={login} onChange={(e) => setLogin(e.target.value)} autoFocus />
          <Entrada rotulo="Senha" type="password" autoComplete="current-password" required value={senha} onChange={(e) => setSenha(e.target.value)} />
          <Botao type="submit" className="w-full" carregando={enviando}>
            Entrar
          </Botao>
        </form>
      </div>
    </main>
  );
}
