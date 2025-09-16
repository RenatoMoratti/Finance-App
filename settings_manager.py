"""
🔧 SETTINGS MANAGER - GERENCIAMENTO DE CONFIGURAÇÕES
=================================================

Gerencia as configurações do sistema em arquivo JSON com criptografia básica.
"""

import json
import os
import base64
from datetime import datetime
from typing import Dict, Optional, List, Tuple

class SettingsManager:
    def __init__(self, settings_file: str = "data/app_settings.json"):
        self.settings_file = settings_file
        self._ensure_settings_directory()
    
    def _ensure_settings_directory(self):
        """Garante que o diretório de configurações existe"""
        try:
            settings_dir = os.path.dirname(self.settings_file)
            if settings_dir and not os.path.exists(settings_dir):
                os.makedirs(settings_dir, exist_ok=True)
        except Exception as e:
            print(f"⚠️ Erro ao criar diretório de configurações: {e}")
    
    def _encode_value(self, value: str) -> str:
        """Codifica um valor usando base64 para ofuscação simples"""
        if not value:
            return value
        try:
            # Adiciona um prefixo para identificar valores codificados
            encoded = base64.b64encode(value.encode('utf-8')).decode('utf-8')
            return f"b64:{encoded}"
        except Exception as e:
            print(f"⚠️ Erro ao codificar valor: {e}")
            return value
    
    def _decode_value(self, encoded_value: str) -> str:
        """Decodifica um valor base64"""
        if not encoded_value:
            return encoded_value
        try:
            # Verifica se tem o prefixo de valor codificado
            if encoded_value.startswith("b64:"):
                decoded = base64.b64decode(encoded_value[4:]).decode('utf-8')
                return decoded
            else:
                # Valor não codificado (compatibilidade com versões antigas)
                return encoded_value
        except Exception as e:
            print(f"⚠️ Erro ao decodificar valor: {e}")
            return encoded_value
    
    def get_settings(self) -> Dict[str, Optional[str]]:
        """Obtém as configurações do arquivo JSON"""
        try:
            if not os.path.exists(self.settings_file):
                return {
                    'flask_secret_key': None,
                    'pluggy_client_id': None,
                    'pluggy_client_secret': None
                }
            
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                encrypted_data = json.load(f)
            
            # Decodifica os valores
            decoded_data = {}
            for key, encoded_value in encrypted_data.items():
                if key in ['flask_secret_key', 'pluggy_client_id', 'pluggy_client_secret']:
                    decoded_data[key] = self._decode_value(encoded_value) if encoded_value else None
                else:
                    decoded_data[key] = encoded_value
            
            return {
                'flask_secret_key': decoded_data.get('flask_secret_key'),
                'pluggy_client_id': decoded_data.get('pluggy_client_id'),
                'pluggy_client_secret': decoded_data.get('pluggy_client_secret')
            }
            
        except Exception as e:
            print(f"❌ Erro ao carregar configurações: {e}")
            return {
                'flask_secret_key': None,
                'pluggy_client_id': None,
                'pluggy_client_secret': None
            }
    
    def save_settings(self, flask_secret_key: str = None, 
                     pluggy_client_id: str = None, 
                     pluggy_client_secret: str = None) -> bool:
        """Salva as configurações no arquivo JSON"""
        try:
            # Carrega configurações existentes
            current_settings = {}
            if os.path.exists(self.settings_file):
                try:
                    with open(self.settings_file, 'r', encoding='utf-8') as f:
                        current_settings = json.load(f)
                except:
                    current_settings = {}
            
            # Atualiza apenas os valores fornecidos
            if flask_secret_key is not None:
                current_settings['flask_secret_key'] = self._encode_value(flask_secret_key)
            
            if pluggy_client_id is not None:
                current_settings['pluggy_client_id'] = self._encode_value(pluggy_client_id)
            
            if pluggy_client_secret is not None:
                current_settings['pluggy_client_secret'] = self._encode_value(pluggy_client_secret)
            
            # Adiciona metadados
            current_settings['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            current_settings['version'] = '1.0'
            
            # Salva o arquivo
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(current_settings, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Configurações salvas em {self.settings_file}")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao salvar configurações: {e}")
            return False
    
    def validate_required_settings(self) -> Tuple[bool, List[str]]:
        """Valida se todas as configurações obrigatórias estão preenchidas"""
        settings = self.get_settings()
        missing_fields = []
        
        if not settings['flask_secret_key'] or settings['flask_secret_key'].strip() == '':
            missing_fields.append('FLASK_SECRET_KEY')
        
        if not settings['pluggy_client_id'] or settings['pluggy_client_id'].strip() == '':
            missing_fields.append('PLUGGY_CLIENT_ID')
        
        if not settings['pluggy_client_secret'] or settings['pluggy_client_secret'].strip() == '':
            missing_fields.append('PLUGGY_CLIENT_SECRET')
        
        return len(missing_fields) == 0, missing_fields
    
    def delete_settings(self) -> bool:
        """Remove o arquivo de configurações"""
        try:
            if os.path.exists(self.settings_file):
                os.remove(self.settings_file)
                print(f"✅ Arquivo de configurações removido: {self.settings_file}")
            return True
        except Exception as e:
            print(f"❌ Erro ao remover configurações: {e}")
            return False

# Instância global para uso na aplicação
settings_manager = SettingsManager()

if __name__ == "__main__":
    # Teste das funcionalidades
    from datetime import datetime
    
    print("🧪 Teste do Settings Manager")
    
    # Teste 1: Salvar configurações
    print("\n1. Salvando configurações de teste...")
    result = settings_manager.save_settings(
        flask_secret_key="test_secret_key_123",
        pluggy_client_id="test_client_id_456",
        pluggy_client_secret="test_client_secret_789"
    )
    print(f"Resultado: {result}")
    
    # Teste 2: Carregar configurações
    print("\n2. Carregando configurações...")
    config = settings_manager.get_settings()
    print(f"Flask Secret Key: {config['flask_secret_key']}")
    print(f"Pluggy Client ID: {config['pluggy_client_id']}")
    print(f"Pluggy Client Secret: {config['pluggy_client_secret']}")
    
    # Teste 3: Validação
    print("\n3. Validando configurações...")
    is_valid, missing = settings_manager.validate_required_settings()
    print(f"Válido: {is_valid}")
    if missing:
        print(f"Campos faltando: {missing}")
    
    print("\n✅ Testes concluídos!")