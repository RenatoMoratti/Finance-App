import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configurações centrais do aplicativo.

    Tudo que possa variar entre ambientes (dev/prod/test) deve vir de
    variável de ambiente ou ter um valor padrão seguro.
    """
    # API Pluggy
    PLUGGY_BASE_URL = os.getenv("PLUGGY_BASE_URL", "https://api.pluggy.ai")
    CLIENT_ID = os.getenv("PLUGGY_CLIENT_ID", "your_client_id_here")
    CLIENT_SECRET = os.getenv("PLUGGY_CLIENT_SECRET", "your_client_secret_here")

    # Flask / Web
    FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "change_me_in_dev_only")
    APP_ENV = os.getenv("APP_ENV", "development")

    # Banco de Dados: separados por ambiente (dev/prod) a menos que DATABASE_PATH seja definido explicitamente.
    _explicit_db = os.getenv("DATABASE_PATH")
    if _explicit_db:
        DATABASE_PATH = _explicit_db
    else:
        if os.getenv("APP_ENV", "development").lower() == "production":
            DATABASE_PATH = "data/finance_app_prod.db"
        else:
            DATABASE_PATH = "data/finance_app_dev.db"

    @staticmethod
    def is_production():
        return Config.APP_ENV.lower() == "production"