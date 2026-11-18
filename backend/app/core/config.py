"""Configuração da aplicação lida de variáveis de ambiente ou do arquivo .env.

Segredos (chave do JWT, segredo do webhook, token do WhatsApp) nunca ficam no código
nem no banco (RNF05): são informados apenas por variáveis de ambiente.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NOME: str = "Confirma Aí"
    APP_VERSAO: str = "0.1.0"
    AMBIENTE: str = "desenvolvimento"  # desenvolvimento | teste | producao

    DATABASE_URL: str = "postgresql+psycopg://confirma:confirma@localhost:5432/confirma_ai"

    # Segurança (RNF04, RNF05)
    SECRET_KEY: str = "chave-de-desenvolvimento-troque-em-producao-0123456789"
    JWT_ALGORITMO: str = "HS256"
    JWT_EXPIRA_MINUTOS: int = 60
    BCRYPT_ROUNDS: int = 12

    # CORS liberado apenas para o front-end (PB02)
    FRONTEND_URL: str = "http://localhost:3000"

    # Fuso usado para "agora" e para os horários da agenda
    FUSO_HORARIO: str = "America/Cuiaba"

    # Mensageria (PB13): "simulador" no desenvolvimento, "whatsapp" com a Cloud API
    MENSAGERIA_PROVEDOR: str = "simulador"
    WEBHOOK_SEGREDO: str = "segredo-webhook-dev"
    SIMULADOR_SUFIXO_FALHA: str = "9999"  # telefones terminados nisso simulam falha de envio

    WHATSAPP_API_URL: str = "https://graph.facebook.com"
    WHATSAPP_API_VERSAO: str = "v21.0"
    WHATSAPP_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_APP_SECRET: str = ""
    WHATSAPP_VERIFY_TOKEN: str = ""
    WHATSAPP_TEMPLATE_LEMBRETE: str = ""
    WHATSAPP_TEMPLATE_OFERTA: str = ""
    WHATSAPP_TEMPLATE_IDIOMA: str = "pt_BR"

    # Tarefas agendadas (APScheduler) e outbox (RNF11, RNF12)
    AGENDADOR_ATIVO: bool = True
    OUTBOX_INTERVALO_SEG: int = 10
    TAREFAS_INTERVALO_SEG: int = 60
    RETENTATIVA_BASE_SEG: int = 30

    # Usuário administrador criado pelo seed
    ADMIN_LOGIN: str = "admin"
    ADMIN_SENHA: str = "Admin@123"
    ADMIN_NOME: str = "Administrador do Sistema"

    @property
    def eh_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
