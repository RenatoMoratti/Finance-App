import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configurações centrais do aplicativo.

    Prioridade de configurações:
    1. Configurações salvas em JSON (settings_manager)
    2. Variáveis de ambiente (.env)
    3. Valores padrão
    """
    
    # Carrega configurações do settings_manager se disponível
    _settings = None
    
    @classmethod
    def _load_settings(cls):
        """Carrega configurações do arquivo JSON"""
        if cls._settings is None:
            try:
                from settings_manager import settings_manager
                cls._settings = settings_manager.get_settings()
            except Exception as e:
                print(f"⚠️ Erro ao carregar configurações JSON: {e}")
                cls._settings = {
                    'flask_secret_key': None,
                    'pluggy_client_id': None,
                    'pluggy_client_secret': None
                }
        return cls._settings
    
    @classmethod
    def reload_from_settings(cls):
        """Força recarregamento das configurações"""
        cls._settings = None
        settings = cls._load_settings()
        
        # Atualiza as variáveis de classe
        if settings['flask_secret_key']:
            cls.FLASK_SECRET_KEY = settings['flask_secret_key']
        if settings['pluggy_client_id']:
            cls.CLIENT_ID = settings['pluggy_client_id']
        if settings['pluggy_client_secret']:
            cls.CLIENT_SECRET = settings['pluggy_client_secret']
    
    # Configurações que vêm das variáveis de ambiente
    PLUGGY_BASE_URL = os.getenv("PLUGGY_BASE_URL", "https://api.pluggy.ai")
    APP_ENV = os.getenv("APP_ENV", "development")
    
    # Banco de Dados
    _explicit_db = os.getenv("DATABASE_PATH")
    if _explicit_db:
        DATABASE_PATH = _explicit_db
    else:
        if os.getenv("APP_ENV", "development").lower() == "production":
            DATABASE_PATH = "data/finance_app_prod.db"
        else:
            DATABASE_PATH = "data/finance_app_dev.db"

# Inicialização das configurações críticas
Config._load_settings()

# API Pluggy - Prioriza JSON, depois .env, depois padrão
_settings = Config._settings
Config.CLIENT_ID = (
    _settings.get('pluggy_client_id') or 
    os.getenv("PLUGGY_CLIENT_ID") or 
    "your_client_id_here"
)
Config.CLIENT_SECRET = (
    _settings.get('pluggy_client_secret') or 
    os.getenv("PLUGGY_CLIENT_SECRET") or 
    "your_client_secret_here"
)

# Flask Secret Key - Prioriza JSON, depois .env, depois padrão
Config.FLASK_SECRET_KEY = (
    _settings.get('flask_secret_key') or 
    os.getenv("FLASK_SECRET_KEY") or 
    "change_me_in_dev_only"
)

@staticmethod
def is_production():
    return Config.APP_ENV.lower() == "production"