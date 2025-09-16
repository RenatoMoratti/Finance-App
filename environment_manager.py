"""
🌍 ENVIRONMENT MANAGER - GERENCIAMENTO DE AMBIENTES
================================================

Gerencia a troca entre ambientes PROD e DEV da aplicação.
"""

import json
import os
from datetime import datetime
from typing import Dict, Tuple

class EnvironmentManager:
    def __init__(self, env_file: str = "data/app_environment.json"):
        self.env_file = env_file
        self._ensure_environment_directory()
        self._initialize_environment()
    
    def _ensure_environment_directory(self):
        """Garante que o diretório de ambiente existe"""
        try:
            env_dir = os.path.dirname(self.env_file)
            if env_dir and not os.path.exists(env_dir):
                os.makedirs(env_dir, exist_ok=True)
        except Exception as e:
            print(f"⚠️ Erro ao criar diretório de ambiente: {e}")
    
    def _initialize_environment(self):
        """Inicializa o arquivo de ambiente se não existir"""
        if not os.path.exists(self.env_file):
            self._save_environment_config("development")
    
    def _save_environment_config(self, environment: str):
        """Salva a configuração do ambiente"""
        try:
            config = {
                "current_environment": environment,
                "last_changed": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "changed_by": "system"
            }
            
            with open(self.env_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
                
            print(f"✅ Ambiente alterado para: {environment.upper()}")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao salvar configuração de ambiente: {e}")
            return False
    
    def get_current_environment(self) -> str:
        """Obtém o ambiente atual"""
        try:
            if os.path.exists(self.env_file):
                with open(self.env_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config.get('current_environment', 'development')
            else:
                return 'development'
        except Exception as e:
            print(f"⚠️ Erro ao ler configuração de ambiente: {e}")
            return 'development'
    
    def switch_environment(self) -> Tuple[bool, str, str]:
        """
        Alterna entre os ambientes PROD e DEV
        
        Returns:
            Tuple[bool, str, str]: (sucesso, ambiente_anterior, ambiente_atual)
        """
        try:
            current_env = self.get_current_environment()
            
            # Alterna o ambiente
            if current_env.lower() == 'development':
                new_env = 'production'
            else:
                new_env = 'development'
            
            success = self._save_environment_config(new_env)
            
            if success:
                return True, current_env, new_env
            else:
                return False, current_env, current_env
                
        except Exception as e:
            print(f"❌ Erro ao alternar ambiente: {e}")
            current_env = self.get_current_environment()
            return False, current_env, current_env
    
    def get_database_path(self) -> str:
        """Retorna o caminho do banco de dados baseado no ambiente atual"""
        env = self.get_current_environment()
        
        if env.lower() == 'production':
            return "data/finance_app_prod.db"
        else:
            return "data/finance_app_dev.db"
    
    def get_settings_file_path(self) -> str:
        """Retorna o caminho do arquivo de configurações baseado no ambiente atual"""
        env = self.get_current_environment()
        
        if env.lower() == 'production':
            return "data/app_settings_prod.json"
        else:
            return "data/app_settings_dev.json"
    
    def get_environment_info(self) -> Dict:
        """Retorna informações completas do ambiente atual"""
        try:
            current_env = self.get_current_environment()
            
            info = {
                'environment': current_env,
                'environment_display': current_env.upper(),
                'database_path': self.get_database_path(),
                'settings_path': self.get_settings_file_path(),
                'is_production': current_env.lower() == 'production',
                'is_development': current_env.lower() == 'development'
            }
            
            # Adiciona informações do arquivo de configuração se existir
            if os.path.exists(self.env_file):
                with open(self.env_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    info['last_changed'] = config.get('last_changed')
                    info['changed_by'] = config.get('changed_by', 'system')
            
            return info
            
        except Exception as e:
            print(f"⚠️ Erro ao obter informações do ambiente: {e}")
            return {
                'environment': 'development',
                'environment_display': 'DEVELOPMENT',
                'database_path': 'data/finance_app_dev.db',
                'settings_path': 'data/app_settings_dev.json',
                'is_production': False,
                'is_development': True
            }

# Instância global para uso na aplicação
environment_manager = EnvironmentManager()

if __name__ == "__main__":
    # Teste das funcionalidades
    print("🧪 Teste do Environment Manager")
    
    # Teste 1: Verificar ambiente atual
    print(f"\n1. Ambiente atual: {environment_manager.get_current_environment()}")
    
    # Teste 2: Informações do ambiente
    print("\n2. Informações do ambiente:")
    info = environment_manager.get_environment_info()
    for key, value in info.items():
        print(f"   {key}: {value}")
    
    # Teste 3: Alternar ambiente
    print(f"\n3. Alternando ambiente...")
    success, old_env, new_env = environment_manager.switch_environment()
    if success:
        print(f"   ✅ Ambiente alterado: {old_env} → {new_env}")
    else:
        print(f"   ❌ Erro ao alterar ambiente")
    
    # Teste 4: Verificar novamente
    print(f"\n4. Ambiente após alteração: {environment_manager.get_current_environment()}")
    
    # Teste 5: Voltar ao ambiente original
    print(f"\n5. Voltando ao ambiente original...")
    success, old_env, new_env = environment_manager.switch_environment()
    if success:
        print(f"   ✅ Ambiente restaurado: {old_env} → {new_env}")
    
    print("\n✅ Testes concluídos!")