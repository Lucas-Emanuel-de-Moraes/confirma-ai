# Confirma Aí

Sistema web de recuperação de vagas perdidas em clínicas, consultórios e unidades de saúde complementar. O objetivo é reduzir o absenteísmo por confirmação antecipada e reaproveitar vagas com uma fila de espera priorizada.

> Projeto acadêmico (TADS – Grupo 2). Todos os dados de demonstração são **fictícios**.

## Fluxo principal

Cadastro → agendamento → lembrete → resposta → identificação de vaga liberada → seleção de paciente elegível → oferta com reserva temporária → aceite atômico → agenda atualizada.

## Estado atual

| Parte | Situação |
|---|---|
| `backend/` | API FastAPI com login, cadastros, agenda, confirmação, fila, recuperação de vagas, LGPD, auditoria e indicadores. 62 testes (pytest). |
| `frontend/` | Interface Next.js com 13 telas, menu por perfil e login. Lint, tipos, testes (Vitest) e build. |
| `.github/workflows/ci.yml` | CI a cada pull request: back-end (ruff, migrations, pytest no PostgreSQL) e front-end (lint, tipos, testes, build). |
| Pendente | Previsão de falta e FHIR apresentados no Problema 3 – ver [`docs/DECISOES.md`](docs/DECISOES.md) (D5). |

## Tecnologias

- **Front-end:** Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS 4, Axios, Vitest.
- **Back-end:** Python 3.12, FastAPI, Pydantic, Uvicorn, JWT + bcrypt.
- **Dados:** PostgreSQL 16, SQLAlchemy 2.0, Alembic.
- **Tarefas e eventos:** APScheduler e tabela outbox.
- **Mensageria:** adaptador com simulador local e WhatsApp Cloud API.

Diferenças em relação ao documento de requisitos estão em [`docs/DECISOES.md`](docs/DECISOES.md).

## Como rodar no Windows (PowerShell)

Pré-requisitos: [Git](https://git-scm.com/download/win), [Python 3.12+](https://www.python.org/downloads/),
[Node.js 22 LTS](https://nodejs.org/) e [Docker Desktop](https://www.docker.com/products/docker-desktop/) (para o PostgreSQL).

**1. Banco** (na pasta do projeto, com o Docker Desktop aberto):

```powershell
docker compose up -d db
```

**2. API** (terminal 1):

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
copy .env.example .env
python -m alembic upgrade head
python -m app.seed --demo
python -m uvicorn app.main:app --reload
```

Teste em http://localhost:8000/api/health e http://localhost:8000/docs.

**3. Front-end** (terminal 2):

```powershell
cd frontend
npm install
copy .env.example .env.local
npm run dev
```

Abra http://localhost:3000 e entre com um usuário de demonstração:

| Login | Senha | Perfil |
|---|---|---|
| `admin` | `Admin@123` | Administrador |
| `recepcao` | `Senha@123` | Recepcionista |
| `gestor` | `Senha@123` | Gestor |
| `profissional` | `Senha@123` | Profissional |

**Testes:** `pytest` em `backend/` e `npm test` em `frontend/`.

Detalhes, WSL/Linux e solução de problemas: [`backend/README.md`](backend/README.md) e [`frontend/README.md`](frontend/README.md).

## Organização

- `backend/` e `frontend/`: código da aplicação.
- `docs/BACKLOG.md`: lista priorizada (PB01–PB38).
- `docs/GUIA-GITHUB.md`: cadastro no GitHub, branches, commits, PR e Definição de Pronto.
- `docs/DECISOES.md`: decisões técnicas e pendências.
- `issues/`: textos das issues (11 épicos e 38 itens do backlog).

## Equipe prevista

Product Owner: Prof. Me. Bruno Ormonde Lima de Oliveira. Scrum Master: Laryssa Vitória. Back-end: Laryssa Vitória e Lucas Emanuel. Front-end: Fabricio Francisco e Maria Eduarda. Atribuições devem ser confirmadas pelo grupo, conforme o documento.

## Fora do escopo inicial

Prontuário eletrônico, telemedicina, faturamento, triagem clínica automatizada, aplicativo móvel nativo, chatbot de orientação clínica e campanhas de marketing.

Fonte: Documento de Requisitos do Sistema Confirma aí - GRUPO 2.pdf, especialmente seções 9–13.
