"""
🔐 OAUTH MANAGER - GERENCIAMENTO DE MÚLTIPLAS CONEXÕES OAUTH
===========================================================

Sistema completo de OAuth para Meu Pluggy com suporte a múltiplas contas:
- Múltiplos item_ids (uma para cada conta bancária)
- Geração de URLs de autorização
- Persistência de tokens
- Renovação automática
- Gerenciamento de conexões
- Integração com app web
"""

import json
import os
import time
import webbrowser
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple, List

class OAuthManager:
    def __init__(self, storage_file: str = "data/oauth_connections.json"):
        self.storage_file = storage_file
        self.ensure_directory()
    
    def ensure_directory(self):
        """Cria diretório se não existir"""
        directory = os.path.dirname(self.storage_file)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
    
    def save_oauth_data(self, item_id: str, bank_name: str = None, status: str = "active", 
                       oauth_url: str = None, expires_at: str = None):
        """Salva dados OAuth para múltiplas conexões"""
        try:
            # Carrega conexões existentes
            connections = self.load_all_connections()
            
            # Cria nova conexão
            connection_data = {
                "item_id": item_id,
                "bank_name": bank_name or f"Banco_{item_id[:8]}",
                "status": status,
                "oauth_url": oauth_url,
                "expires_at": expires_at,
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                # Campo opcional: filtrar transações a partir desta data (YYYY-MM-DD)
                "data_since": None
            }
            
            # Adiciona ou atualiza conexão
            connections[item_id] = connection_data
            
            # Salva todas as conexões
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(connections, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"❌ Erro ao salvar OAuth: {e}")
            return False
    
    def load_oauth_data(self) -> Optional[Dict]:
        """Carrega dados OAuth salvos (compatibilidade com versão anterior)"""
        connections = self.load_all_connections()
        if connections:
            # Retorna a primeira conexão ativa para compatibilidade
            for item_id, data in connections.items():
                if data.get('status') == 'active':
                    return data
        return None
    
    def load_all_connections(self) -> Dict:
        """Carrega todas as conexões OAuth"""
        try:
            if not os.path.exists(self.storage_file):
                return {}
            
            with open(self.storage_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Se for o formato antigo (single connection), converte
            if isinstance(data, dict) and 'item_id' in data:
                old_data = data
                new_format = {
                    old_data['item_id']: {
                        "item_id": old_data['item_id'],
                        "bank_name": "Conta Principal",
                        "status": old_data.get('status', 'active'),
                        "oauth_url": old_data.get('oauth_url'),
                        "expires_at": old_data.get('expires_at'),
                        "created_at": old_data.get('created_at'),
                        "last_updated": old_data.get('last_updated')
                    }
                }
                # Salva no novo formato
                with open(self.storage_file, 'w', encoding='utf-8') as f:
                    json.dump(new_format, f, indent=2, ensure_ascii=False)
                return new_format
            
            # Garante que cada conexão tenha o campo data_since
            updated = False
            for item_id, conn in data.items():
                if 'data_since' not in conn:
                    conn['data_since'] = None
                    updated = True
            if updated:
                try:
                    with open(self.storage_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                except Exception:
                    pass
            return data
        except Exception as e:
            print(f"❌ Erro ao carregar OAuth: {e}")
            return {}
    
    def has_valid_connection(self) -> bool:
        """Verifica se há pelo menos uma conexão OAuth válida"""
        connections = self.load_all_connections()
        return any(
            conn.get('status') == 'active' and conn.get('item_id')
            for conn in connections.values()
        )
    
    def get_item_id(self) -> Optional[str]:
        """Obtém item_id da primeira conexão ativa (compatibilidade)"""
        connections = self.load_all_connections()
        for item_id, data in connections.items():
            if data.get('status') == 'active':
                return item_id
        return None
    
    def get_all_item_ids(self) -> List[str]:
        """Obtém todos os item_ids ativos"""
        connections = self.load_all_connections()
        return [
            item_id for item_id, data in connections.items()
            if data.get('status') == 'active'
        ]
    
    def get_active_connections(self) -> Dict:
        """Obtém todas as conexões ativas"""
        connections = self.load_all_connections()
        return {
            item_id: data for item_id, data in connections.items()
            if data.get('status') == 'active'
        }
    
    def get_connection_info(self, item_id: str) -> Optional[Dict]:
        """Obtém informações de uma conexão específica"""
        connections = self.load_all_connections()
        return connections.get(item_id)
    
    def update_connection_name(self, item_id: str, bank_name: str):
        """Atualiza nome da conexão"""
        connections = self.load_all_connections()
        if item_id in connections:
            connections[item_id]['bank_name'] = bank_name
            connections[item_id]['last_updated'] = datetime.now().isoformat()
            
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(connections, f, indent=2, ensure_ascii=False)
            return True
        return False
    
    def update_status(self, item_id: str, status: str):
        """Atualiza status de uma conexão específica"""
        connections = self.load_all_connections()
        if item_id in connections:
            connections[item_id]['status'] = status
            connections[item_id]['last_updated'] = datetime.now().isoformat()
            
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(connections, f, indent=2, ensure_ascii=False)
            return True
        return False
    
    def remove_connection(self, item_id: str):
        """Remove uma conexão específica"""
        connections = self.load_all_connections()
        if item_id in connections:
            del connections[item_id]
            
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(connections, f, indent=2, ensure_ascii=False)
            return True
        return False
    
    def clear_oauth_data(self):
        """Remove TODAS as conexões OAuth (para reconectar tudo)"""
        try:
            if os.path.exists(self.storage_file):
                os.remove(self.storage_file)
            return True
        except Exception as e:
            print(f"❌ Erro ao limpar OAuth: {e}")
            return False
    
    def get_connections_summary(self) -> Dict:
        """Obtém resumo de todas as conexões"""
        connections = self.load_all_connections()
        active_count = sum(1 for conn in connections.values() if conn.get('status') == 'active')
        
        return {
            'total_connections': len(connections),
            'active_connections': active_count,
            'inactive_connections': len(connections) - active_count,
            'connections': connections
        }
    
    def get_all_connections(self):
        """Retorna todas as conexões no formato compatível com templates"""
        connections = self.load_all_connections()
        
        # Converte para formato esperado pelos templates
        formatted_connections = {}
        for connection_id, connection_data in connections.items():
            formatted_connections[connection_id] = {
                'name': connection_data.get('bank_name', connection_id),
                'status': connection_data.get('status', 'unknown'),
                'created_at': connection_data.get('created_at'),
                'item_id': connection_data.get('item_id'),
                'data_since': connection_data.get('data_since')
            }
        
        return formatted_connections

    def update_data_since(self, item_id: str, data_since: str | None):
        """Atualiza (ou limpa) a data inicial de importação de transações da conexão.

        data_since: string YYYY-MM-DD ou None para remover filtro.
        """
        connections = self.load_all_connections()
        if item_id in connections:
            # Validação simples de formato
            if data_since:
                if len(data_since) != 10:
                    return False
                try:
                    datetime.strptime(data_since, '%Y-%m-%d')
                except ValueError:
                    return False
            connections[item_id]['data_since'] = data_since
            connections[item_id]['last_updated'] = datetime.now().isoformat()
            try:
                with open(self.storage_file, 'w', encoding='utf-8') as f:
                    json.dump(connections, f, indent=2, ensure_ascii=False)
                return True
            except Exception as e:
                print(f"❌ Erro ao salvar data_since: {e}")
                return False
        return False
