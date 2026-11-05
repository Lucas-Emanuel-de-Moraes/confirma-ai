# Confirma Aí – front-end (Next.js)

Interface web do Confirma Aí, consumindo a API FastAPI do diretório `../backend`.

**Stack:** Next.js 16 (App Router) · React 19 · TypeScript · Tailwind CSS 4 · Axios. Sem outras bibliotecas de UI, formulário ou estado.

## Como rodar

Pré-requisito: API no ar em `http://localhost:8000` (veja `../backend/README.md`).

```bash
npm install
cp .env.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
npm run dev                  # http://localhost:3000
```

O endereço do front precisa estar em `FRONTEND_URL` no `.env` do back-end (CORS). Se o Next subir em outra porta
(ex.: 3001 porque a 3000 está ocupada), inclua-a: `FRONTEND_URL=http://localhost:3000,http://localhost:3001`.

Usuários de demonstração (criados por `python -m app.seed --demo`): `admin` / `Admin@123`;
`recepcao`, `gestor`, `profissional` / `Senha@123`.

Outros comandos: `npm run build` (build de produção), `npm run lint`.

## Organização

```
src/
  app/
    login/              tela de login (POST /auth/login)
    (app)/              área autenticada – layout com menu filtrado por perfil
      page.tsx          painel do dia
      agenda/           agendamentos, histórico, cancelamento, comparecimento
      remarcacoes/      pendências de remarcação (HU02)
      fila/             fila de espera e preferências de encaixe
      vagas/            vagas liberadas e ofertas (aceite/recusa/cancelamento)
      pacientes/        cadastro + autorização de contato (LGPD)
      estrutura/        unidades, especialidades, profissionais, horários, bloqueios
      parametros/       parâmetros operacionais versionados
      indicadores/      absenteísmo, confirmação e recuperação
      lgpd/             requisições do titular e retenção
      usuarios/         usuários e perfis
      auditoria/        logs de auditoria
      simulador/        caixa de saída do WhatsApp simulado + tarefas agendadas
  lib/
    api.ts              instância do axios, token, tratamento de erro { codigo, mensagem, campos }
    auth.tsx            contexto de autenticação (token JWT no localStorage)
    permissoes.ts       espelho dos perfis/permissões do back-end (só para esconder telas)
    types.ts            tipos dos schemas da API
    formato.ts          datas, telefones, rótulos de status
  hooks/
    useApi.ts           useConsulta (GET), useAcao (escritas), useDebounce
    useCadastros.ts     unidades/especialidades/profissionais para selects
  components/           AppShell, selos de status, seletor de paciente, UI base (ui/)
```

## Decisões

- **Token no `localStorage`**: o interceptor do axios envia `Authorization: Bearer`; um 401 limpa a sessão e volta ao login.
- **Permissões**: o menu e os botões seguem o perfil do usuário, mas quem decide é a API (403 é exibido como aviso).
- **Datas**: a API trabalha com horário local da clínica sem fuso (`2026-11-10T09:00:00`); o front não converte fuso.
- **Busca de dados**: hooks próprios sobre o axios, sem biblioteca de cache.
