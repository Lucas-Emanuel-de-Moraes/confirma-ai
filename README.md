# Confirma Aí

Sistema web de recuperação de vagas perdidas em clínicas, consultórios e unidades de saúde complementar. O objetivo é reduzir o absenteísmo por confirmação antecipada e reaproveitar vagas com uma fila de espera priorizada.

## Estado deste pacote

Planejamento preparado para cadastro no GitHub. Não contém implementação executável nem configurações de CI já operacionais. A publicação do repositório, das issues e do quadro ainda precisa ser realizada.

## Fluxo principal

Cadastro → agendamento → lembrete → resposta → identificação de vaga liberada → seleção de paciente elegível → oferta com reserva temporária → aceite atômico → agenda atualizada.

## Tecnologias definidas no documento

- Front-end: React 18, TypeScript, Next.js, App Router e Axios.
- Back-end: Python 3.12, FastAPI, Pydantic e Uvicorn.
- Dados: PostgreSQL 16, SQLAlchemy 2.0 e Alembic.
- Tarefas e eventos: APScheduler e tabela outbox.
- Mensageria: adaptador com simulador local e WhatsApp Cloud API.
- Testes previstos: pytest e Vitest; integração contínua com GitHub Actions.

Arquitetura: monólito modular em camadas, conforme seção 11 do PDF. As versões acima são as especificadas no documento; versões de dependências devem ser compatibilizadas durante a implementação.

## Organização

- `issues/epicos/`: 11 textos de issues agrupadoras.
- `issues/backlog/`: 38 textos de issues do produto.
- `docs/BACKLOG.md`: lista priorizada.
- `docs/GUIA-GITHUB.md`: procedimento de criação e regras da equipe.

## Equipe prevista

Product Owner: Prof. Me. Bruno Ormonde Lima de Oliveira. Scrum Master: Laryssa Vitória. Back-end: Laryssa Vitória e Lucas Emanuel. Front-end: Fabricio Francisco e Maria Eduarda. Atribuições devem ser confirmadas pelo grupo, conforme o documento.

## Fora do escopo inicial

Prontuário eletrônico, telemedicina, faturamento, triagem clínica automatizada, aplicativo móvel nativo, chatbot de orientação clínica e campanhas de marketing.

## Execução

Ainda não disponível neste pacote de planejamento. PB02–PB04 devem implementar e documentar a inicialização da API, banco e front-end; PB01 só estará concluído com instruções verificadas e CI em funcionamento.

Fonte: Documento de Requisitos do Sistema Confirma aí - GRUPO 2.pdf, especialmente seções 9–13.
