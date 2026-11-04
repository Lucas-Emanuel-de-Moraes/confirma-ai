# Confirma Aí – Back-end

Back-end do **Confirma Aí – Sistema de Recuperação de Vagas Perdidas** (Grupo 2), construído conforme
o Documento de Requisitos (RF01–RF24, RN01–RN20, RNF01–RNF19) e as seções 9–13 (backlog e arquitetura):

- **Python 3.12 + FastAPI** (funciona a partir do 3.10), servidor **Uvicorn**
- **PostgreSQL 16** + **SQLAlchemy 2.0** + **Alembic** (migrations)
- **APScheduler** + tabela **outbox** (lembretes, envio com retentativas, expiração de ofertas, retenção)
- **OAuth2 com senha + JWT**, senhas com **bcrypt**, autorização por perfil
- Adaptador de mensageria com **simulador local** e **WhatsApp Cloud API** atrás da mesma interface
- **OpenAPI** automático em `/docs`, métricas **Prometheus** em `/metrics`
- **62 testes automatizados** (pytest), incluindo concorrência real no PostgreSQL

---

## Sumário
1. [Passo a passo no Ubuntu (WSL)](#1-passo-a-passo-no-ubuntu-wsl)
2. [Rodar os testes automatizados](#2-rodar-os-testes-automatizados)
3. [Ver o fluxo completo funcionando](#3-ver-o-fluxo-completo-funcionando)
4. [Testar manualmente pelo Swagger](#4-testar-manualmente-pelo-swagger-docs)
5. [Alternativa: tudo em Docker](#5-alternativa-tudo-em-docker)
6. [Problemas comuns no WSL](#6-problemas-comuns-no-wsl)
7. [O que foi implementado](#7-o-que-foi-implementado)

---

## 1. Passo a passo no Ubuntu (WSL)

> Todos os comandos são digitados no terminal do **Ubuntu** (WSL), não no PowerShell.

### 1.1 Instalar o que falta

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip unzip
python3 --version        # precisa ser 3.10 ou mais novo
```

**Docker** (para o PostgreSQL). Escolha **uma** opção:

- **Opção A – Docker Desktop no Windows** (mais simples): instale o Docker Desktop, abra
  *Settings → Resources → WSL integration* e ative a sua distribuição Ubuntu. Depois, no Ubuntu:
  ```bash
  docker --version && docker compose version
  ```
- **Opção B – Docker dentro do Ubuntu**:
  ```bash
  sudo apt install -y docker.io docker-compose-v2
  sudo usermod -aG docker $USER
  sudo service docker start
  ```
  Feche e abra o terminal do Ubuntu (para o grupo `docker` valer) e teste com `docker ps`.

*(Sem Docker? Veja a seção 6, item "Usar PostgreSQL instalado no Ubuntu".)*

### 1.2 Copiar o projeto para o Ubuntu

Baixe o `confirma-ai.zip` no Windows e copie para a sua pasta no Linux
(troque `SEU_USUARIO` pelo seu usuário do Windows):

```bash
cp /mnt/c/Users/SEU_USUARIO/Downloads/confirma-ai.zip ~/
cd ~
unzip confirma-ai.zip
cd confirma-ai
```

> Dica: deixe o projeto em `~/` (sistema de arquivos do Linux), e não em `/mnt/c/...` – fica muito mais rápido.

### 1.3 Subir o banco PostgreSQL

```bash
docker compose up -d db
docker compose ps          # aguarde o STATUS ficar "healthy"
```

Isso cria o banco `confirma_ai` (usuário/senha `confirma`/`confirma`) e também o banco
`confirma_ai_test`, usado pelos testes.

### 1.4 Criar o ambiente Python e instalar as dependências

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # o prompt passa a mostrar (.venv)
pip install --upgrade pip
pip install -e ".[dev]"
```

> Sempre que abrir um terminal novo: `cd ~/confirma-ai/backend && source .venv/bin/activate`.

### 1.5 Configurar o `.env`

```bash
cp .env.example .env
# opcional (recomendado): gere uma chave nova e cole em SECRET_KEY no .env
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

### 1.6 Criar as tabelas e os dados iniciais

```bash
alembic upgrade head              # aplica a migration (cria as 30 tabelas)
python -m app.seed --demo         # perfis, admin e dados FICTÍCIOS de demonstração
```

O seed cria os usuários:

| Login          | Senha       | Perfil         |
|----------------|-------------|----------------|
| `admin`        | `Admin@123` | Administrador  |
| `recepcao`     | `Senha@123` | Recepcionista  |
| `gestor`       | `Senha@123` | Gestor         |
| `profissional` | `Senha@123` | Profissional   |

…e a "Clínica Central", Cardiologia/Dermatologia/Clínica Geral, 3 profissionais com horário todos os
dias das 07h às 22h, 5 pacientes fictícios com contato autorizado e João e Helena (prioridade ALTA) na
fila de Cardiologia.

### 1.7 Rodar a API

```bash
uvicorn app.main:app --reload
```

Abra no navegador do Windows:

- **http://localhost:8000/api/health** → deve mostrar `"status": "ok"` e `"banco": "ok"`
- **http://localhost:8000/docs** → documentação interativa (Swagger) para testar os endpoints
- http://localhost:8000/redoc e http://localhost:8000/metrics

Para parar a API: `Ctrl + C`. Para parar o banco: `docker compose stop db` (na pasta `confirma-ai`).

---

## 2. Rodar os testes automatizados

Com o venv ativo, dentro de `backend/`:

```bash
pytest                     # rápido: usa SQLite em memória (os 3 testes de concorrência são pulados)
```

Para rodar **tudo no PostgreSQL**, inclusive os testes de concorrência (dupla marcação com threads):

```bash
TEST_DATABASE_URL=postgresql+psycopg://confirma:confirma@localhost:5432/confirma_ai_test pytest -v
```

Resultado esperado: `62 passed`. Verificação de estilo: `ruff check .`

| Arquivo de teste | O que verifica |
|---|---|
| `test_acesso.py` | health, login/JWT, 401/403 por perfil, usuário inativo, auditoria do login |
| `test_cadastros.py` | HU01 (validação, telefone duplicado, inativação), UC01 (duplicados, horário conflitante) |
| `test_agenda.py` | UC02, dupla marcação (409), fora do horário, bloqueio/feriado, transições de status |
| `test_confirmacao.py` | lembrete na antecedência, SIM/NÃO/REMARCAR, respostas forjadas/reutilizadas/expiradas |
| `test_recuperacao.py` | prioridade e desempate, elegibilidade, reserva, recusa, expiração, aceite atômico |
| `test_notificacao.py` | outbox idempotente, retentativas, falha definitiva → reoferta, revogação imediata |
| `test_lgpd.py` | histórico de consentimento, acesso/correção/eliminação, retenção, auditoria imutável |
| `test_remarcacao_parametros_indicadores.py` | HU02, parâmetros versionados, indicadores |
| `test_concorrencia.py` | 4 aceites simultâneos → só 1 vence; índice parcial; agendamentos simultâneos |
| `test_whatsapp.py` | formato da Cloud API, assinatura `X-Hub-Signature-256`, leitura do webhook |

---

## 3. Ver o fluxo completo funcionando

Com a API rodando (passo 1.7), abra **outro terminal** do Ubuntu:

```bash
cd ~/confirma-ai/backend && source .venv/bin/activate
python scripts/demo_fluxo.py
```

O script executa, pela API, o cenário da seção 2.3 do documento e mostra cada etapa com ✔:

1. a recepção agenda a Maria para amanhã; uma segunda marcação no mesmo horário recebe **409**;
2. o sistema envia o lembrete (WhatsApp simulado);
3. uma resposta **forjada** (outro telefone) é descartada;
4. Maria responde **NÃO** → a vaga é liberada e oferecida à **Helena** (prioridade ALTA);
5. a recepção tenta usar o horário reservado → **409 VAGA_RESERVADA**;
6. Helena **recusa** → a oferta vai para o **João**, que **aceita** → novo agendamento;
7. linha do tempo do agendamento e indicadores do gestor.

O script pode ser repetido quantas vezes quiser.

---

## 4. Testar manualmente pelo Swagger (`/docs`)

1. Em **http://localhost:8000/docs** clique em **Authorize**, informe `username` = `recepcao` e
   `password` = `Senha@123` e confirme. (Para tarefas e auditoria, use `admin` / `Admin@123`.)
2. **Crie um agendamento** – `POST /api/v1/agendamentos`:
   ```json
   { "paciente_id": 1, "unidade_id": 1, "especialidade_id": 1, "profissional_id": 1,
     "data_hora": "2026-11-06T10:00:00" }
   ```
   (use a data de amanhã). Repita o mesmo corpo com `"paciente_id": 4` → **409 HORARIO_OCUPADO**.
3. **Envie o lembrete** – o agendador faz isso sozinho a cada 60 s, mas para não esperar: entre como
   `admin` e execute `POST /api/v1/tarefas/ciclo`.
4. **Veja a mensagem enviada** – `GET /api/v1/simulador/mensagens` e copie o `identificador`.
5. **Responda como o paciente** – `POST /api/v1/simulador/responder`:
   ```json
   { "telefone": "5565999990001", "identificador": "COLE_AQUI", "resposta": "NAO" }
   ```
   Teste também `SIM`, `REMARCAR`, um telefone diferente ou o mesmo identificador duas vezes.
6. **Acompanhe a recuperação** – `POST /api/v1/tarefas/outbox`, depois `GET /api/v1/ofertas`,
   `GET /api/v1/vagas` e `GET /api/v1/simulador/mensagens?telefone=5565999990003` (Helena).
   Responda `ACEITAR` ou `RECUSAR` com o identificador da oferta.
7. **Confira o resultado** – `GET /api/v1/agendamentos`, `GET /api/v1/agendamentos/{id}/historico`,
   `GET /api/v1/indicadores` (perfil gestor) e `GET /api/v1/auditoria` (admin).

Outras coisas para experimentar: `DELETE /api/v1/pacientes/{id}/autorizacao` (revogar contato – nenhuma
mensagem é enviada depois), `GET /api/v1/remarcacoes` + `PATCH /api/v1/remarcacoes/{id}`,
`PUT /api/v1/unidades/1/parametros`, `POST /api/v1/requisicoes-titular` (LGPD) e o paciente
"Paciente Falha Envio" (telefone final 9999), para o qual o simulador sempre falha – útil para ver as
retentativas e a falha definitiva.

Exemplo com `curl` (sem Swagger):

```bash
TOKEN=$(curl -s -X POST localhost:8000/api/v1/auth/login -d "username=recepcao&password=Senha@123" \
        | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
curl -s localhost:8000/api/v1/pacientes -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

---

## 5. Alternativa: tudo em Docker

Sem instalar Python, na pasta `confirma-ai`:

```bash
docker compose up --build
```

O contêiner da API aplica as migrations, roda o seed de demonstração e sobe em
http://localhost:8000/docs. Para rodar os testes dentro dele:

```bash
docker compose exec api pytest
```

Backup e restauração do banco (RNF17): `backend/scripts/backup.sh` e
`backend/scripts/restaurar.sh backups/<arquivo>.sql.gz`.

---

## 6. Problemas comuns no WSL

| Sintoma | Solução |
|---|---|
| `Cannot connect to the Docker daemon` | Opção A: abra o Docker Desktop. Opção B: `sudo service docker start`. |
| `permission denied ... docker.sock` | `sudo usermod -aG docker $USER`, feche e reabra o terminal (ou `wsl --shutdown` no PowerShell). |
| `port 5432 already allocated` | Há outro PostgreSQL no Windows. No `docker-compose.yml` troque para `"5433:5432"` e no `.env` use `localhost:5433`. |
| `connection refused` ao rodar `alembic` | O banco não está de pé: `docker compose up -d db` e `docker compose ps`. |
| `ensurepip is not available` | `sudo apt install -y python3-venv` |
| `database "confirma_ai_test" does not exist` | O volume foi criado antes do script: `docker exec confirma-ai-db createdb -U confirma confirma_ai_test` |
| `localhost:8000` não abre no navegador | Use o IP do WSL: `hostname -I` → `http://IP:8000/docs` e rode `uvicorn app.main:app --reload --host 0.0.0.0`. |
| Horários estranhos | O fuso é `FUSO_HORARIO` no `.env` (padrão `America/Cuiaba`). |

**Usar PostgreSQL instalado no Ubuntu (sem Docker):**

```bash
sudo apt install -y postgresql
sudo service postgresql start
sudo -u postgres psql -c "CREATE USER confirma WITH PASSWORD 'confirma' CREATEDB;"
sudo -u postgres psql -c "CREATE DATABASE confirma_ai OWNER confirma;"
sudo -u postgres psql -c "CREATE DATABASE confirma_ai_test OWNER confirma;"
```

Depois siga a partir do passo 1.4.

---

## 7. O que foi implementado

### Estrutura (seção 11.9)

```
confirma-ai/
├── backend/
│   ├── app/
│   │   ├── main.py            cria o app FastAPI e registra os routers
│   │   ├── tarefas.py         APScheduler + POST /tarefas/{nome}
│   │   ├── seed.py            perfis, admin e dados de demonstração
│   │   ├── core/              configuração · segurança (JWT/bcrypt) · banco · erros · eventos · métricas
│   │   └── modules/           cada um com models · schemas · repository · service · router
│   │       ├── acesso/        login, usuários, perfis e permissões
│   │       ├── cadastros/     pacientes, unidades, especialidades, profissionais, horários, bloqueios
│   │       ├── agenda/        agendamentos, status, histórico, comparecimento
│   │       ├── confirmacao/   lembretes, webhook, validação de vínculo (UC13)
│   │       ├── fila/          fila de espera, preferências de encaixe, remarcações
│   │       ├── recuperacao/   vagas liberadas, elegibilidade, priorização, ofertas, aceite atômico
│   │       ├── parametros/    parâmetros e regra de elegibilidade versionados por unidade
│   │       ├── lgpd/          consentimento, requisições do titular, retenção
│   │       ├── notificacao/   gateway · simulador · whatsapp · outbox
│   │       ├── auditoria/     LogAuditoria somente inserção
│   │       └── indicadores/   absenteísmo, confirmação, recuperação, ocupação
│   ├── alembic/versions/      migration 0001 (inclui gatilho que bloqueia UPDATE/DELETE na auditoria)
│   ├── tests/                 62 testes pytest
│   └── scripts/               demo_fluxo.py · backup.sh · restaurar.sh
├── docker-compose.yml
└── .github/workflows/ci.yml   ruff + alembic upgrade/check + pytest no PostgreSQL
```

### Itens do backlog cobertos (frente Back)

PB01 (CI), PB02, PB03, PB05–PB28, PB30–PB33, PB35 (backup) – ou seja, a parte de back-end de todas as
sprints S1 a S8. Ficaram de fora, como "Futuro" no próprio backlog: **PB37** (MFA – o campo
`mfa_habilitado` já existe) e **PB38** (sincronização com sistema externo). PB36 (teste de carga) não
foi incluído. As telas (PB04, PB29, PB34 e a parte Front dos itens F + B) são do front-end.

### Como os requisitos críticos foram atendidos

| Requisito | Implementação |
|---|---|
| RF17 / RN13 / RNF03 – sem dupla marcação | `SELECT … FOR UPDATE` na oferta e na vaga + coluna `versao` + índices únicos parciais em `agendamento` e `oferta_vaga`; o perdedor recebe **409** |
| RN02 – reserva temporária | horário com oferta `RESERVADA` não pode ser agendado pela recepção |
| RF24 / RN20 / RNF19 – vínculo da resposta | identificador aleatório de uso único com validade; telefone e autorização conferidos; inválidas registradas |
| RN16 – revogação imediata | consentimento verificado ao enfileirar **e** no envio; revogar cancela mensagens na fila e reservas abertas |
| RNF11 / RNF12 – mensageria confiável | outbox na mesma transação, retentativas 30 s → 60 s → 120 s, chave de idempotência |
| RN09 / RN10 – priorização | prioridade assistencial (se a regra permitir) → data de entrada → id; critério gravado na oferta |
| RN12 / RN17 – auditoria | `log_auditoria` somente inserção (ORM + gatilho no PostgreSQL), sem dados sensíveis |
| RN18 / RN19 – LGPD | eliminação vira **uso restrito** quando há registros obrigatórios; expurgo por categoria auditado |

### Decisões que complementam o documento

- **Tabelas acrescentadas** ao diagrama de classes: `vaga_liberada` (ciclo de vida da vaga e
  indicadores), `historico_status_agendamento` (RF07), `historico_consentimento` (RF21),
  `solicitacao_remarcacao` (HU02), `horario_atendimento` e `bloqueio_agenda` (UC01, RN14),
  `outbox_evento` e `politica_retencao` (já previstas na seção 11.6).
- O índice único `(profissional_id, data_hora)` é **parcial** (só status que ocupam a vaga), senão
  o horário cancelado nunca poderia ser reaproveitado.
- Especialidade e profissional desejados ficam na entrada da **fila**; a `PreferenciaEncaixe` guarda
  unidade, período e data.
- Parâmetro extra `antecedencia_minima_oferta_min` (padrão 120 min) define a "janela configurada" do RF11.
- Trocar o telefone do paciente exige nova autorização de contato.
- O paciente pode responder **SAIR** para revogar a autorização pelo próprio WhatsApp.
- Um encaixe aceito cria agendamento `AGENDADO`, recomeçando o fluxo de lembrete (seção 2.3).
- **HTTPS (RNF06):** localmente a API roda em HTTP; em produção deve ficar atrás de um proxy com TLS.
- O adaptador **WhatsApp** segue a documentação da Cloud API, mas só pode ser validado com conta
  comercial verificada e mensagens-modelo aprovadas; por isso o padrão é o simulador.

### Endpoints principais (prefixo `/api/v1`)

`/auth/login` · `/auth/me` · `/usuarios` · `/pacientes` · `/pacientes/{id}/autorizacao` ·
`/pacientes/{id}/consentimento` · `/unidades` · `/unidades/{id}/parametros` · `/especialidades` ·
`/profissionais` · `/profissionais/{id}/horarios` · `/bloqueios` · `/agendamentos` ·
`/agendamentos/{id}/historico` · `/agendamentos/{id}/cancelar` · `/agendamentos/{id}/comparecimento` ·
`/remarcacoes` · `/fila-espera` · `/fila-espera/{id}/preferencias` · `/vagas` · `/ofertas` ·
`/ofertas/{id}/aceitar|recusar|cancelar` · `/indicadores` · `/requisicoes-titular` ·
`/retencao/politicas` · `/retencao/executar` · `/auditoria` · `/webhooks/mensageria` ·
`/tarefas/{nome}` · `/simulador/mensagens` · `/simulador/responder` — e `/api/health`, `/metrics`.
A lista completa, com exemplos, está em `/docs`.
