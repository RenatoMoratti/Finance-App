"""
≡ƒùä∩╕Å DATABASE - GERENCIAMENTO DO BANCO DE DADOS
==============================================

Sistema de banco de dados SQLite para armazenar:
- C        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Usar hor├írio de Bras├¡lia para timestamps
            current_timestamp = get_brasilia_time()
            
            # Registra o hist├│rico de sincroniza├º├úo
            cursor.execute('''
                INSERT INTO sync_history (item_id, accounts_count, transactions_count, sync_date, modification_date)
                VALUES (?, ?, ?, ?, ?)
            ''', (item_id, len(accounts), len(transactions), current_timestamp, current_timestamp))rias
- Transa├º├╡es
- Hist├│rico de sincroniza├º├╡es
"""

import sqlite3
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional

def get_brasilia_time():
    """Retorna o horário atual de Brasília (UTC-3)"""
    utc_now = datetime.now(timezone.utc)
    brasilia_tz = timezone(timedelta(hours=-3))
    return utc_now.astimezone(brasilia_tz).strftime('%Y-%m-%d %H:%M:%S')

def convert_iso_to_standard_format(iso_date_str):
    """
    Converte data do formato ISO 8601 (2025-08-06T22:57:30.102Z) 
    para o formato padrão (YYYY-MM-DD HH:MM:SS)
    
    IMPORTANTE: Para transações, mantém consistência com o formato já armazenado no banco
    para evitar atualizações desnecessárias por diferenças de timezone.
    """
    if not iso_date_str:
        return None
    
    try:
        # Se já está no formato padrão, retorna como está
        if not ('T' in iso_date_str and 'Z' in iso_date_str):
            return iso_date_str
        
        # Remove microsegundos e 'Z' se presentes
        clean_date = iso_date_str.replace('Z', '+00:00')
        
        # Parse da data ISO 8601
        dt = datetime.fromisoformat(clean_date.split('.')[0] + '+00:00')
        
        # Para datas de transações que são apenas datas (00:00:00 UTC), 
        # mantém apenas a data sem conversão de timezone para evitar mudança de dia
        if dt.time() == dt.time().replace(hour=0, minute=0, second=0, microsecond=0):
            # Se é meia-noite UTC, provavelmente é só uma data, mantém a data original
            return dt.strftime('%Y-%m-%d 00:00:00')
        
        # Para horários específicos, converte para Brasília
        brasilia_tz = timezone(timedelta(hours=-3))
        dt_brasilia = dt.astimezone(brasilia_tz)
        
        # Retorna no formato padrão
        return dt_brasilia.strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, AttributeError) as e:
        print(f"Erro ao converter data '{iso_date_str}': {e}")
        return iso_date_str  # Retorna original se houver erro

def normalize_date_for_comparison(date_str):
    """
    Normaliza datas para comparação, garantindo mesmo formato e lidando com timezones
    
    IMPORTANTE: Foco em evitar falsos positivos que causam atualizações desnecessárias
    """
    if not date_str:
        return ""
    
    # Converte para string se não for
    date_str = str(date_str).strip()
    
    try:
        # Se contém informações de timezone, remove para comparar apenas data/hora local
        if '+' in date_str or 'Z' in date_str:
            # Remove timezone info para comparação local
            date_str = date_str.replace('Z', '').split('+')[0]
        
        # Padroniza formato para YYYY-MM-DD HH:MM:SS
        if 'T' in date_str:
            # ISO format with T
            parts = date_str.split('T')
            date_part = parts[0]
            time_part = parts[1].split('.')[0] if len(parts) > 1 else '00:00:00'
        else:
            # Space separated or date only
            if ' ' in date_str:
                date_part, time_part = date_str.split(' ', 1)
                time_part = time_part.split('.')[0]  # Remove microseconds
            else:
                date_part = date_str
                time_part = '00:00:00'
        
        # Ensure time has seconds
        time_parts = time_part.split(':')
        if len(time_parts) == 2:
            time_part += ':00'
        elif len(time_parts) == 1:
            time_part += ':00:00'
        
        normalized = f"{date_part} {time_part}"
        
        # Tenta parsear para validar o formato
        datetime.strptime(normalized, '%Y-%m-%d %H:%M:%S')
        
        return normalized
        
    except (ValueError, AttributeError, IndexError):
        # Se falhar na normalização, retorna string original limpa
        return str(date_str).strip()

def generate_conflict_log(existing_data: dict, new_data: dict) -> str:
    """Gera um log de conflito legível em UTF-8, detalhando campo e valores.

    Formato:
    [CONFLITO] 2025-09-08 09:34:33
    • Valor: R$ 10,00 → R$ 12,50
    • Descrição: 'ANTIGA' → 'NOVA'
    • Data: 2025-09-01 10:00:00 → 2025-09-01 13:00:00
    • Categoria: 'Alimentação' → 'Mercado'
    • Tipo: CREDIT → DEBIT
    """
    differences = []
    timestamp = get_brasilia_time()

    # Valor
    try:
        old_amount = float(existing_data.get('amount', 0) or 0)
        new_amount = float(new_data.get('amount', 0) or 0)
        if abs(old_amount - new_amount) > 0.01:
            differences.append(("Valor", f"R$ {old_amount:.2f}", f"R$ {new_amount:.2f}"))
    except (TypeError, ValueError):
        pass

    # Descrição
    if existing_data.get('description') != new_data.get('description'):
        differences.append(("Descrição", f"'{existing_data.get('description', '')}'", f"'{new_data.get('description', '')}'"))

    # Data (normalizada para evitar falsos positivos de timezone)
    existing_date_normalized = normalize_date_for_comparison(existing_data.get('date'))
    new_date_normalized = normalize_date_for_comparison(new_data.get('date'))
    if existing_date_normalized != new_date_normalized:
        differences.append(("Data", existing_data.get('date', ''), new_data.get('date', '')))

    # Categoria
    if existing_data.get('category') != new_data.get('category'):
        differences.append(("Categoria", f"'{existing_data.get('category', '')}'", f"'{new_data.get('category', '')}'"))

    # Tipo (se presente)
    if existing_data.get('type') != new_data.get('type'):
        differences.append(("Tipo", existing_data.get('type', ''), new_data.get('type', '')))

    if not differences:
        return ""

    lines = [f"[CONFLITO] {timestamp}"]
    for label, old, new in differences:
        lines.append(f"• {label}: {old} → {new}")
    return "\n".join(lines)

class Database:
    def __init__(self, db_path: str | None = None):
        # Permite injetar caminho; se não informado usa variável de ambiente (via Config)
        if db_path is None:
            try:
                from config import Config
                self.db_path = getattr(Config, 'DATABASE_PATH', 'data/finance_app_dev.db')
            except Exception:
                self.db_path = 'data/finance_app_dev.db'
        else:
            self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Inicializa o banco de dados com as tabelas necess├írias"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabela de sincroniza├º├╡es
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id TEXT,
                sync_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                accounts_count INTEGER,
                transactions_count INTEGER,
                status TEXT DEFAULT 'success',
                modification_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de contas com connection_name
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                id TEXT PRIMARY KEY,
                name TEXT,
                type TEXT,
                subtype TEXT,
                balance REAL,
                currency_code TEXT,
                item_id TEXT,
                connection_name TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                modification_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de transa├º├╡es com connection_name
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                account_id TEXT,
                account_name TEXT,
                amount REAL,
                description TEXT,
                transaction_date TIMESTAMP,
                category TEXT,
                type TEXT,
                item_id TEXT,
                connection_name TEXT,
                creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                modification_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                manual_modification INTEGER DEFAULT 0,
                FOREIGN KEY (account_id) REFERENCES accounts (id)
            )
        ''')
        
        # Tabela de categorias e subcategorias personalizadas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                subcategory TEXT,
                transaction_type TEXT NOT NULL CHECK (transaction_type IN ('CREDIT', 'DEBIT')),
                description TEXT,
                color TEXT,
                icon TEXT,
                is_active INTEGER DEFAULT 1,
                creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                modification_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, subcategory, transaction_type)
            )
        ''')
        
        # Tabela de divisão por conta (percentuais para Usuário 1 e Usuário 2)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS account_splits (
                account_id TEXT PRIMARY KEY,
                user1_percent REAL NOT NULL DEFAULT 50.0,
                user2_percent REAL NOT NULL DEFAULT 50.0,
                creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                modification_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES accounts (id)
            )
        ''')

        # Tabela de configurações da página Divisão (nomes dos usuários)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS division_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                user1_name TEXT DEFAULT 'Usuário 1',
                user2_name TEXT DEFAULT 'Usuário 2',
                creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                modification_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Garante registro padrão na tabela de configurações (id = 1)
        try:
            cursor.execute('SELECT COUNT(*) FROM division_settings WHERE id = 1')
            row = cursor.fetchone()
            if row and row[0] == 0:
                current_timestamp = get_brasilia_time()
                cursor.execute('''
                    INSERT INTO division_settings (id, user1_name, user2_name, creation_date, modification_date)
                    VALUES (1, 'Usuário 1', 'Usuário 2', ?, ?)
                ''', (current_timestamp, current_timestamp))
        except sqlite3.OperationalError:
            # Em caso de corrida de migração
            pass
        
        # Migration: Add new columns and rename existing ones
        self._migrate_database_schema(cursor)
        
        conn.commit()
        conn.close()
    
    def _migrate_database_schema(self, cursor):
        """Migrates existing database schema to new requirements"""
        try:
            # Add connection_name columns if not exist (for existing databases)
            try:
                cursor.execute('ALTER TABLE accounts ADD COLUMN connection_name TEXT')
            except sqlite3.OperationalError:
                pass
                
            try:
                cursor.execute('ALTER TABLE transactions ADD COLUMN connection_name TEXT')
            except sqlite3.OperationalError:
                pass
            
            # Add modification_date columns to all tables
            try:
                cursor.execute('ALTER TABLE sync_history ADD COLUMN modification_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
            except sqlite3.OperationalError:
                pass
                
            try:
                cursor.execute('ALTER TABLE accounts ADD COLUMN modification_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
            except sqlite3.OperationalError:
                pass
                
            try:
                cursor.execute('ALTER TABLE transactions ADD COLUMN modification_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
            except sqlite3.OperationalError:
                pass
            
            # Add creation_date columns
            try:
                cursor.execute('ALTER TABLE accounts ADD COLUMN creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
            except sqlite3.OperationalError:
                pass
                
            try:
                cursor.execute('ALTER TABLE transactions ADD COLUMN creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
            except sqlite3.OperationalError:
                pass
            
            # Add verified column for transaction verification status
            try:
                cursor.execute('ALTER TABLE transactions ADD COLUMN verified INTEGER DEFAULT 0')
            except sqlite3.OperationalError:
                pass
            
            # Add conflict_detected column for sync conflicts
            try:
                cursor.execute('ALTER TABLE transactions ADD COLUMN conflict_detected INTEGER DEFAULT 0')
            except sqlite3.OperationalError:
                pass
            
            # Add conflict_log column for detailed conflict information
            try:
                cursor.execute('ALTER TABLE transactions ADD COLUMN conflict_log TEXT')
            except sqlite3.OperationalError:
                pass
            
            # Add manual_modification column to track manual edits
            try:
                cursor.execute('ALTER TABLE transactions ADD COLUMN manual_modification INTEGER DEFAULT 0')
            except sqlite3.OperationalError:
                pass
            
            # Add user_category and user_subcategory columns for custom categories
            try:
                cursor.execute('ALTER TABLE transactions ADD COLUMN user_category TEXT')
            except sqlite3.OperationalError:
                pass
                
            try:
                cursor.execute('ALTER TABLE transactions ADD COLUMN user_subcategory TEXT')
            except sqlite3.OperationalError:
                pass
            
            # Add ignorar_transacao column for ignoring transactions in calculations
            try:
                cursor.execute('ALTER TABLE transactions ADD COLUMN ignorar_transacao INTEGER DEFAULT 0')
            except sqlite3.OperationalError:
                pass

            # Add per-transaction split percentage columns
            try:
                cursor.execute('ALTER TABLE transactions ADD COLUMN user1_percent REAL')
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute('ALTER TABLE transactions ADD COLUMN user2_percent REAL')
            except sqlite3.OperationalError:
                pass
            
            # Rename date to transaction_date in transactions table (only if old column exists)
            # Check if 'date' column exists and 'transaction_date' doesn't
            cursor.execute("PRAGMA table_info(transactions)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'date' in columns and 'transaction_date' not in columns:
                # SQLite doesn't support column renaming directly, so we need to:
                # 1. Add new column
                # 2. Copy data
                # 3. Keep old column for backward compatibility
                cursor.execute('ALTER TABLE transactions ADD COLUMN transaction_date TIMESTAMP')
                cursor.execute('UPDATE transactions SET transaction_date = date WHERE transaction_date IS NULL')
            
            # Update modification_date for existing records that don't have it
            cursor.execute('UPDATE sync_history SET modification_date = sync_date WHERE modification_date IS NULL')
            cursor.execute('UPDATE accounts SET modification_date = last_updated WHERE modification_date IS NULL')
            cursor.execute('UPDATE accounts SET creation_date = last_updated WHERE creation_date IS NULL')
            cursor.execute('UPDATE transactions SET modification_date = transaction_date WHERE modification_date IS NULL')
            cursor.execute('UPDATE transactions SET creation_date = transaction_date WHERE creation_date IS NULL')

            # NORMALIZAÇÃO: garantir que todos os valores de transações fiquem armazenados como absolutos (>=0)
            # Idempotente: pode ser executado múltiplas vezes sem efeitos colaterais
            try:
                cursor.execute('UPDATE transactions SET amount = ABS(amount)')
            except sqlite3.OperationalError:
                pass

            # Criar tabela de mapeamento de categorias da API -> categorias do usuário (de-para)
            try:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS category_mappings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        source_category TEXT NOT NULL,
                        transaction_type TEXT,
                        mapped_user_category TEXT,
                        mapped_user_subcategory TEXT,
                        needs_classification INTEGER DEFAULT 1,
                        creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        modification_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(source_category, transaction_type)
                    )
                ''')
            except sqlite3.OperationalError:
                pass
            
        except Exception as e:
            print(f"ΓÜá∩╕Å Warning during database migration: {e}")
    
    def save_sync_data(self, item_id: str, accounts: List[Dict], transactions: List[Dict]) -> bool:
        """Salva dados de sincroniza├º├úo no banco"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            current_timestamp = datetime.now().isoformat()
            
            # Registra a sincronização
            cursor.execute('''
                INSERT INTO sync_history (item_id, accounts_count, transactions_count, sync_date, modification_date)
                VALUES (?, ?, ?, ?, ?)
            ''', (item_id, len(accounts), len(transactions), current_timestamp, current_timestamp))
            
            # Limpa dados antigos por item_id (mant├⌐m compatibilidade)
            cursor.execute('DELETE FROM accounts WHERE item_id = ?', (item_id,))
            cursor.execute('DELETE FROM transactions WHERE item_id = ?', (item_id,))
            
            # Salva contas
            for account in accounts:
                cursor.execute('''
                    INSERT OR REPLACE INTO accounts 
                    (id, name, type, subtype, balance, currency_code, item_id, connection_name, creation_date, modification_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    account.get('id'),
                    account.get('name'),
                    account.get('type'),
                    account.get('subtype'),
                    account.get('balance', 0),
                    account.get('currencyCode', 'BRL'),
                    item_id,
                    account.get('connection_name', 'N/A'),
                    current_timestamp,
                    current_timestamp
                ))
            
            # Salva transa├º├╡es
            for transaction in transactions:
                transaction_id = transaction.get('id')
                
                # Verifica se a transa├º├úo j├í existe e est├í verificada
                cursor.execute('SELECT verified FROM transactions WHERE id = ?', (transaction_id,))
                existing = cursor.fetchone()
                
                if existing and existing[0]:  # Se existe e est├í verificada
                    # Marca poss├¡vel conflito mas n├úo substitui
                    cursor.execute('''
                        UPDATE transactions 
                        SET conflict_detected = 1
                        WHERE id = ?
                    ''', (transaction_id,))
                    print(f"ΓÜá∩╕Å Transa├º├úo verificada protegida: {transaction_id[:8]}...")
                else:
                    # Transação não existe ou não está verificada - pode substituir
                    # Desmarca conflict_detected ao atualizar
                    transaction_date = convert_iso_to_standard_format(transaction.get('date'))
                    cursor.execute('''
                        INSERT OR REPLACE INTO transactions 
                        (id, account_id, account_name, amount, description, transaction_date, category, type, item_id, connection_name, creation_date, modification_date, manual_modification)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                    ''', (
                        transaction.get('id'),
                        transaction.get('accountId'),
                        transaction.get('account_name'),
                        abs(transaction.get('amount', 0) or 0),  # sempre valor absoluto
                        transaction.get('description'),
                        transaction_date,
                        transaction.get('category'),
                        transaction.get('type'),
                        item_id,
                        transaction.get('connection_name', 'N/A'),
                        current_timestamp,
                        current_timestamp
                    ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Γ¥î Erro ao salvar no banco: {e}")
            return False
    
    def get_last_sync(self) -> Optional[Dict]:
        """Obt├⌐m informa├º├╡es da ├║ltima sincroniza├º├úo"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT sync_date, accounts_count, transactions_count, status
                FROM sync_history 
                ORDER BY sync_date DESC 
                LIMIT 1
            ''')
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'sync_date': result[0],
                    'accounts_count': result[1],
                    'transactions_count': result[2],
                    'status': result[3]
                }
            return None
            
        except Exception as e:
            print(f"Γ¥î Erro ao buscar ├║ltima sincroniza├º├úo: {e}")
            return None
    
    def get_accounts_summary(self) -> List[Dict]:
        """Obtém resumo das contas com informação se é manual ou de conexão"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, name, type, subtype, balance, currency_code, last_updated, 
                       creation_date, modification_date, connection_name, item_id
                FROM accounts 
                ORDER BY 
                    CASE WHEN connection_name IS NULL OR connection_name = '' THEN 0 ELSE 1 END,
                    balance DESC
            ''')
            
            accounts = []
            for row in cursor.fetchall():
                # Determinar se é conta manual ou de conexão
                is_manual = row[9] is None or row[9] == '' or row[10] is None or row[10] == ''
                
                accounts.append({
                    'id': row[0],
                    'name': row[1],
                    'type': row[2],
                    'subtype': row[3],
                    'balance': row[4],
                    'currency_code': row[5],
                    'last_updated': row[6],
                    'creation_date': row[7],
                    'modification_date': row[8],
                    'connection_name': row[9],
                    'item_id': row[10],
                    'is_manual': is_manual,
                    'source_type': 'Manual' if is_manual else 'Conexão'
                })
            
            conn.close()
            return accounts
            
        except Exception as e:
            print(f"❌ Erro ao buscar contas: {e}")
            return []
    
    def get_transactions(self, limit: int = 100, account_id: str = None, 
                        start_date: str = None, end_date: str = None) -> List[Dict]:
        """Obt├⌐m transa├º├╡es com filtros"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = '''
                SELECT id, account_id, account_name, amount, description, 
                       transaction_date, 
                       category, type, creation_date, modification_date,
                       date(transaction_date) as date_only,
                       time(transaction_date) as time_only
                FROM transactions 
                WHERE 1=1
            '''
            params = []
            
            if account_id:
                query += ' AND account_id = ?'
                params.append(account_id)
            
            if start_date:
                # Se o formato incluir 'T' (datetime-local), usar datetime completo
                if 'T' in start_date:
                    query += ' AND datetime(transaction_date) >= datetime(?)'
                else:
                    query += ' AND date(transaction_date) >= ?'
                params.append(start_date)
            
            if end_date:
                # Se o formato incluir 'T' (datetime-local), usar datetime completo
                if 'T' in end_date:
                    query += ' AND datetime(transaction_date) <= datetime(?)'
                else:
                    query += ' AND date(transaction_date) <= ?'
                params.append(end_date)
            
            query += ' ORDER BY transaction_date DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            
            transactions = []
            for row in cursor.fetchall():
                transactions.append({
                    'id': row[0],
                    'account_id': row[1],
                    'account_name': row[2],
                    'amount': row[3],
                    'description': row[4],
                    'transaction_date': row[5],
                    'category': row[6],
                    'type': row[7],
                    'creation_date': row[8],
                    'modification_date': row[9],
                    'date_only': row[10],
                    'time_only': row[11]
                })
            
            conn.close()
            return transactions
            
        except Exception as e:
            print(f"Γ¥î Erro ao buscar transa├º├╡es: {e}")
            return []
    
    def get_transactions_with_connection_info(self, limit: int = 100, account_id: List[str] = None, 
                                             connection_id: str = None, start_date: str = None, 
                                             end_date: str = None, category: str = None,
                                             user_category: List[str] = None, user_subcategory: List[str] = None,
                                             modification_start_date: str = None, 
                                             modification_end_date: str = None,
                                             verification_filter: List[str] = None) -> List[Dict]:
        """Obt├⌐m transa├º├╡es com informa├º├╡es da conex├úo e conta, incluindo filtro por data de modifica├º├úo"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = '''
                SELECT 
                    t.id, t.account_id, t.account_name, t.amount, t.description, 
                    t.transaction_date, 
                    t.category, t.type, t.creation_date, t.modification_date,
                    t.connection_name as connection_name,
                    a.name as account_full_name,
                    date(t.transaction_date) as date_only,
                    time(t.transaction_date) as time_only,
                    COALESCE(t.verified, 0) as verified,
                    COALESCE(t.conflict_detected, 0) as conflict_detected,
                    COALESCE(t.conflict_log, '') as conflict_log,
                    COALESCE(t.ignorar_transacao, 0) as ignorar_transacao,
                    COALESCE(t.manual_modification, 0) as manual_modification,
                    t.user_category,
                    t.user_subcategory,
                    COALESCE(t.user1_percent, s.user1_percent, 50.0) AS user1_percent,
                    COALESCE(t.user2_percent, s.user2_percent, 50.0) AS user2_percent
                FROM transactions t
                LEFT JOIN accounts a ON t.account_id = a.id
                LEFT JOIN account_splits s ON s.account_id = t.account_id
                WHERE 1=1
            '''
            params = []
            
            if account_id and len(account_id) > 0:
                # Filtro múltiplo para contas
                placeholders = ','.join('?' * len(account_id))
                query += f' AND t.account_id IN ({placeholders})'
                params.extend(account_id)
                
            if connection_id:
                query += ' AND t.connection_name = ?'
                params.append(connection_id)
            
            if start_date:
                # Se o formato incluir 'T' (datetime-local), usar datetime completo
                if 'T' in start_date:
                    query += ' AND datetime(t.transaction_date) >= datetime(?)'
                else:
                    query += ' AND date(t.transaction_date) >= ?'
                params.append(start_date)
            
            if end_date:
                # Se o formato incluir 'T' (datetime-local), usar datetime completo
                if 'T' in end_date:
                    query += ' AND datetime(t.transaction_date) <= datetime(?)'
                else:
                    query += ' AND date(t.transaction_date) <= ?'
                params.append(end_date)
            
            if category:
                query += ' AND t.category = ?'
                params.append(category)
            
            if user_category and len(user_category) > 0:
                # Filtro múltiplo para categorias de usuário
                conditions = []
                for cat in user_category:
                    if cat == '__sem_categoria__':
                        conditions.append('(t.user_category IS NULL OR t.user_category = "")')
                    else:
                        conditions.append('t.user_category = ?')
                        params.append(cat)
                
                if conditions:
                    query += f' AND ({" OR ".join(conditions)})'
            
            if user_subcategory and len(user_subcategory) > 0:
                # Filtro múltiplo para subcategorias de usuário
                conditions = []
                for subcat in user_subcategory:
                    if subcat == '__sem_subcategoria__':
                        conditions.append('(t.user_subcategory IS NULL OR t.user_subcategory = "")')
                    else:
                        conditions.append('t.user_subcategory = ?')
                        params.append(subcat)
                
                if conditions:
                    query += f' AND ({" OR ".join(conditions)})'
            
            if modification_start_date:
                # Se o formato incluir 'T' (datetime-local), usar datetime completo
                if 'T' in modification_start_date:
                    query += ' AND datetime(t.modification_date) >= datetime(?)'
                else:
                    query += ' AND date(t.modification_date) >= ?'
                params.append(modification_start_date)
            
            if modification_end_date:
                # Se o formato incluir 'T' (datetime-local), usar datetime completo
                if 'T' in modification_end_date:
                    query += ' AND datetime(t.modification_date) <= datetime(?)'
                else:
                    query += ' AND date(t.modification_date) <= ?'
                params.append(modification_end_date)
            
            if verification_filter and len(verification_filter) > 0:
                # Filtro múltiplo para status de verificação
                conditions = []
                for status in verification_filter:
                    if status == 'verified':
                        conditions.append('t.verified = 1')
                    elif status == 'not_verified':
                        conditions.append('(t.verified = 0 OR t.verified IS NULL)')
                    elif status == 'with_conflicts':
                        conditions.append('t.conflict_detected = 1')
                
                if conditions:
                    query += f' AND ({" OR ".join(conditions)})'
            
            query += ' ORDER BY t.transaction_date DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)

            transactions = []
            for row in cursor.fetchall():
                transactions.append({
                    'id': row[0],
                    'account_id': row[1],
                    'account_name': row[2],
                    'amount': row[3],
                    'description': row[4],
                    'transaction_date': row[5],
                    'category': row[6],
                    'type': row[7],
                    'creation_date': row[8],
                    'modification_date': row[9],
                    'connection_name': row[10] or 'N/A',
                    'account_full_name': row[11] or row[2],
                    'date_only': row[12],
                    'time_only': row[13],
                    'verified': row[14],
                    'conflict_detected': row[15],
                    'conflict_log': row[16] or '',
                    'ignorar_transacao': row[17],
                    'manual_modification': row[18],
            'user_category': row[19],
            'user_subcategory': row[20],
            'user1_percent': row[21],
            'user2_percent': row[22]
                })

            conn.close()
            return transactions
            
        except Exception as e:
            print(f"Γ¥î Erro ao buscar transa├º├╡es com informa├º├╡es de conex├úo: {e}")
            return []

    def get_categories(self) -> List[str]:
        """Obt├⌐m todas as categorias dispon├¡veis nas transa├º├╡es"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT DISTINCT category
                FROM transactions 
                WHERE category IS NOT NULL AND category != ''
                ORDER BY category
            ''')
            
            categories = [row[0] for row in cursor.fetchall()]
            conn.close()
            return categories
            
        except Exception as e:
            print(f"Γ¥î Erro ao buscar categorias: {e}")
            return []

    def get_transaction_by_id(self, transaction_id: str) -> Dict:
        """Busca uma transa├º├úo espec├¡fica pelo ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, account_id, account_name, amount, description, 
                       transaction_date, 
                       category, type, item_id, connection_name, creation_date, modification_date,
                       COALESCE(manual_modification, 0) as manual_modification
                FROM transactions 
                WHERE id = ?
            ''', (transaction_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'id': row[0],
                    'account_id': row[1],
                    'account_name': row[2],
                    'amount': row[3],
                    'description': row[4],
                    'transaction_date': row[5],
                    'category': row[6],
                    'type': row[7],
                    'item_id': row[8],
                    'connection_name': row[9],
                    'creation_date': row[10],
                    'modification_date': row[11],
                    'manual_modification': row[12]
                }
            else:
                return None
            
        except Exception as e:
            print(f"Γ¥î Erro ao buscar transa├º├úo: {e}")
            return None

    def update_transaction(self, transaction_id: str, amount: float, description: str, 
                          category: str, transaction_date: str, account_id: str = None, 
                          transaction_type: str = None) -> bool:
        """Atualiza uma transação específica - preserva segundos originais se data não mudou"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Busca a transação atual para comparar a data
            cursor.execute('SELECT transaction_date FROM transactions WHERE id = ?', (transaction_id,))
            current_result = cursor.fetchone()
            
            if not current_result:
                conn.close()
                return False
            
            current_date = current_result[0]
            
            # Compara apenas data + hora:minuto (ignora segundos)
            def extract_date_hour_minute(date_str):
                """Extrai YYYY-MM-DD HH:MM de uma string de data"""
                if not date_str:
                    return ""
                # Remove segundos e microssegundos se existirem
                if len(date_str) > 16:
                    return date_str[:16]
                return date_str
            
            current_date_hm = extract_date_hour_minute(current_date)
            new_date_hm = extract_date_hour_minute(transaction_date)
            
            # Se a data+hora:minuto não mudou, preserva a data original (com segundos)
            final_transaction_date = current_date if current_date_hm == new_date_hm else transaction_date
            
            # Obtém horário de Brasília para modification_date
            brasilia_time = get_brasilia_time()
            
            # NOVO PADRÃO: armazenar sempre valor absoluto; direção representada apenas pelo campo type
            final_amount = abs(amount)
            
            # Monta a query de atualização - marca como modificação manual
            query_parts = ['amount = ?', 'description = ?', 'category = ?', 'transaction_date = ?', 'modification_date = ?']
            params = [final_amount, description, category, final_transaction_date, brasilia_time]
            
            # Se transaction_type foi fornecido, adiciona na query
            if transaction_type:
                query_parts.append('type = ?')
                params.append(transaction_type)
            
            # Se account_id foi fornecido, adiciona na query
            if account_id:
                # Busca o nome da conta
                cursor.execute('SELECT name FROM accounts WHERE id = ?', (account_id,))
                account_result = cursor.fetchone()
                account_name = account_result[0] if account_result else 'Conta Desconhecida'
                
                query_parts.extend(['account_id = ?', 'account_name = ?'])
                params.extend([account_id, account_name])
            
            # Sempre marca como modificação manual
            query_parts.append('manual_modification = 1')
            
            # Monta a query final
            query = f'''
                UPDATE transactions 
                SET {', '.join(query_parts)}
                WHERE id = ?
            '''
            params.append(transaction_id)
            
            cursor.execute(query, params)
            
            # Verifica se alguma linha foi afetada
            rows_affected = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            return rows_affected > 0
            
        except Exception as e:
            print(f"Γ¥î Erro ao atualizar transa├º├úo: {e}")
            return False

    def get_statistics(self) -> Dict:
        """Obt├⌐m estat├¡sticas gerais"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Total de contas e saldo
            cursor.execute('SELECT COUNT(*), SUM(balance) FROM accounts')
            accounts_count, total_balance = cursor.fetchone()
            
            # Total de transa├º├╡es
            cursor.execute('SELECT COUNT(*) FROM transactions')
            transactions_count = cursor.fetchone()[0]
            
            # Receitas e despesas (├║ltimos 30 dias)
            # Com valores armazenados sempre como absolutos, usamos o campo type para determinar direção
            cursor.execute('''
                SELECT 
                    SUM(CASE WHEN type = 'CREDIT' THEN amount ELSE 0 END) as income,
                    SUM(CASE WHEN type = 'DEBIT' THEN amount ELSE 0 END) as expense
                FROM transactions 
                WHERE date(transaction_date) >= date('now', '-30 days')
            ''')
            income, expense = cursor.fetchone()
            
            conn.close()
            
            monthly_income = income or 0
            monthly_expense = expense or 0
            return {
                'accounts_count': accounts_count or 0,
                'total_balance': total_balance or 0,
                'transactions_count': transactions_count or 0,
                'monthly_income': monthly_income,
                'monthly_expense': monthly_expense,
                'monthly_net': monthly_income - monthly_expense
            }
            
        except Exception as e:
            print(f"Γ¥î Erro ao buscar estat├¡sticas: {e}")
            return {}

    def update_modification_date(self, table: str, record_id: str) -> bool:
        """Atualiza a data de modifica├º├úo de um registro espec├¡fico"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Usar hor├írio de Bras├¡lia
            current_timestamp = get_brasilia_time()
            
            if table == 'accounts':
                cursor.execute('''
                    UPDATE accounts 
                    SET modification_date = ? 
                    WHERE id = ?
                ''', (current_timestamp, record_id))
            elif table == 'transactions':
                cursor.execute('''
                    UPDATE transactions 
                    SET modification_date = ? 
                    WHERE id = ?
                ''', (current_timestamp, record_id))
            elif table == 'sync_history':
                cursor.execute('''
                    UPDATE sync_history 
                    SET modification_date = ? 
                    WHERE id = ?
                ''', (current_timestamp, record_id))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Γ¥î Erro ao atualizar data de modifica├º├úo: {e}")
            return False

    def update_account(self, account_id: str, **kwargs) -> bool:
        """Atualiza uma conta e sua data de modifica├º├úo"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Constr├│i query dinamicamente baseada nos kwargs
            set_clauses = []
            params = []
            
            for key, value in kwargs.items():
                if key in ['name', 'type', 'subtype', 'balance', 'currency_code', 'connection_name']:
                    set_clauses.append(f"{key} = ?")
                    params.append(value)
            
            if set_clauses:
                # Adiciona atualiza├º├úo da data de modifica├º├úo
                set_clauses.append("modification_date = ?")
                params.append(datetime.now().isoformat())
                params.append(account_id)
                
                query = f"UPDATE accounts SET {', '.join(set_clauses)} WHERE id = ?"
                cursor.execute(query, params)
                
                conn.commit()
                conn.close()
                return True
            
            return False
            
        except Exception as e:
            print(f"Γ¥î Erro ao atualizar conta: {e}")
            return False

    def save_sync_data_incremental(self, item_id: str, accounts: List[Dict], transactions: List[Dict]) -> bool:
        """Salva dados de sincroniza├º├úo de forma incremental (apenas novos ou modificados)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            current_timestamp = datetime.now().isoformat()
            
            # Registra a sincroniza├º├úo
            cursor.execute('''
                INSERT INTO sync_history (item_id, accounts_count, transactions_count, modification_date)
                VALUES (?, ?, ?, ?)
            ''', (item_id, len(accounts), len(transactions), current_timestamp))
            
            # Estat├¡sticas para log
            accounts_inserted = 0
            accounts_updated = 0
            accounts_unchanged = 0
            transactions_inserted = 0
            transactions_updated = 0
            transactions_unchanged = 0
            conflicts_detected = 0
            
            # Processa contas de forma incremental
            for account in accounts:
                account_id = account.get('id')
                
                # Busca conta existente
                cursor.execute('SELECT id, name, balance, currency_code FROM accounts WHERE id = ?', (account_id,))
                existing_account = cursor.fetchone()
                
                if existing_account:
                    # Verifica se houve mudan├ºas significativas
                    existing_name = existing_account[1]
                    existing_balance = existing_account[2]
                    existing_currency = existing_account[3]
                    
                    new_name = account.get('name')
                    new_balance = account.get('balance', 0)
                    new_currency = account.get('currencyCode', 'BRL')
                    
                    # Compara se houve mudan├ºas
                    has_changes = (
                        existing_name != new_name or
                        abs(existing_balance - new_balance) > 0.01 or  # Toler├óncia para valores decimais
                        existing_currency != new_currency
                    )
                    
                    if has_changes:
                        # Atualiza registro existente
                        cursor.execute('''
                            UPDATE accounts 
                            SET name=?, type=?, subtype=?, balance=?, currency_code=?, 
                                item_id=?, connection_name=?, modification_date=?
                            WHERE id=?
                        ''', (
                            new_name, account.get('type'), account.get('subtype'),
                            new_balance, new_currency, item_id,
                            account.get('connection_name', 'N/A'), current_timestamp, account_id
                        ))
                        accounts_updated += 1
                    else:
                        accounts_unchanged += 1
                else:
                    # Insere nova conta
                    cursor.execute('''
                        INSERT INTO accounts 
                        (id, name, type, subtype, balance, currency_code, item_id, connection_name, creation_date, modification_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        account_id, account.get('name'), account.get('type'), account.get('subtype'),
                        account.get('balance', 0), account.get('currencyCode', 'BRL'), item_id,
                        account.get('connection_name', 'N/A'), current_timestamp, current_timestamp
                    ))
                    accounts_inserted += 1
            
            # Processa transa├º├╡es de forma incremental
            for transaction in transactions:
                transaction_id = transaction.get('id')
                
                # Busca transa├º├úo existente
                cursor.execute('SELECT id, amount, description, transaction_date, verified, type, category FROM transactions WHERE id = ?', (transaction_id,))
                existing_transaction = cursor.fetchone()
                
                if existing_transaction:
                    # Verifica se a transa├º├úo est├í marcada como verificada
                    is_verified = existing_transaction[4] if len(existing_transaction) > 4 else 0
                    
                    if is_verified:
                        # Transa├º├úo verificada - n├úo atualiza, mas marca poss├¡vel conflito
                        existing_amount = existing_transaction[1]
                        existing_description = existing_transaction[2]
                        existing_date = existing_transaction[3]
                        existing_type = existing_transaction[5] if len(existing_transaction) > 5 else None
                        existing_category = existing_transaction[6] if len(existing_transaction) > 6 else None
                        existing_category = existing_transaction[6] if len(existing_transaction) > 6 else None
                        
                        new_amount = abs(transaction.get('amount', 0) or 0)
                        new_description = transaction.get('description')
                        new_date_raw = transaction.get('date')
                        new_type = transaction.get('type')
                        new_category = transaction.get('category')
                        new_category = transaction.get('category')
                        
                        # Converte a data da API para BRL antes da comparação
                        new_date_converted = convert_iso_to_standard_format(new_date_raw)
                        
                        # Verifica se haveria mudanças usando datas normalizadas no mesmo fuso
                        existing_date_normalized = normalize_date_for_comparison(existing_date)
                        new_date_normalized = normalize_date_for_comparison(new_date_converted)
                        
                        has_conflicts = (
                            abs(existing_amount - new_amount) > 0.01 or  # Tolerância para valores decimais
                            existing_description != new_description or
                            existing_date_normalized != new_date_normalized or
                            existing_type != new_type or
                            existing_category != new_category
                        )
                        
                        if has_conflicts:
                            # Gera log detalhado do conflito
                            existing_data = {
                                'amount': existing_amount,
                                'description': existing_description,
                                'date': existing_date,
                                'type': existing_type,
                                'category': existing_category
                            }
                            new_data = {
                                'amount': new_amount,
                                'description': new_description,
                                'date': new_date_converted,
                                'type': new_type,
                                'category': new_category
                            }
                            conflict_log = generate_conflict_log(existing_data, new_data)
                            
                            # Marca como conflito detectado mas n├úo altera os dados
                            cursor.execute('''
                                UPDATE transactions 
                                SET conflict_detected = 1, conflict_log = ?
                                WHERE id = ?
                            ''', (conflict_log, transaction_id))
                            print(f"ΓÜá∩╕Å Conflito detectado na transa├º├úo verificada {transaction_id[:8]}... - dados protegidos")
                            conflicts_detected += 1
                        
                        transactions_unchanged += 1
                        continue
                    
                    # Transa├º├úo n├úo verificada - procede com verifica├º├úo normal de mudan├ºas
                    existing_amount = existing_transaction[1]
                    existing_description = existing_transaction[2]
                    existing_date = existing_transaction[3]
                    existing_type = existing_transaction[5] if len(existing_transaction) > 5 else None
                    
                    new_amount = abs(transaction.get('amount', 0) or 0)
                    new_description = transaction.get('description')
                    new_date = transaction.get('date')
                    new_type = transaction.get('type')
                    
                    # Compara se houve mudan├ºas
                    existing_date_normalized = normalize_date_for_comparison(existing_date)
                    new_date_normalized = normalize_date_for_comparison(new_date)
                    
                    has_changes = (
                        abs(existing_amount - new_amount) > 0.01 or  # Tolerância para valores decimais
                        existing_description != new_description or
                        existing_date_normalized != new_date_normalized or
                        existing_type != new_type  # Verificação do tipo também
                    )
                    
                    if has_changes:
                        # Atualiza registro existente e desmarca conflict_detected e manual_modification se existia
                        transaction_date = convert_iso_to_standard_format(transaction.get('date'))
                        cursor.execute('''
                            UPDATE transactions 
                            SET account_id=?, account_name=?, amount=?, description=?, transaction_date=?, 
                                category=?, type=?, item_id=?, connection_name=?, modification_date=?, 
                                conflict_detected=0, manual_modification=0
                            WHERE id=?
                        ''', (
                            transaction.get('accountId'), transaction.get('account_name'),
                            new_amount, new_description, transaction_date,
                            transaction.get('category'), transaction.get('type'), item_id,
                            transaction.get('connection_name', 'N/A'), current_timestamp, transaction_id
                        ))
                        transactions_updated += 1
                    else:
                        transactions_unchanged += 1
                else:
                    # Insere nova transação
                    transaction_date = convert_iso_to_standard_format(transaction.get('date'))
                    cursor.execute('''
                        INSERT INTO transactions 
                        (id, account_id, account_name, amount, description, transaction_date, category, type, item_id, connection_name, creation_date, modification_date, manual_modification)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                    ''', (
                        transaction_id, transaction.get('accountId'), transaction.get('account_name'),
                        abs(transaction.get('amount', 0) or 0), transaction.get('description'), transaction_date,
                        transaction.get('category'), transaction.get('type'), item_id,
                        transaction.get('connection_name', 'N/A'), current_timestamp, current_timestamp
                    ))
                    transactions_inserted += 1
            
            conn.commit()
            conn.close()
            
            # Log detalhado da sincroniza├º├úo incremental
            connections_processed = len(set(t.get('connection_name', 'N/A') for t in transactions)) if transactions else 0
            print(f"≡ƒôè Sincroniza├º├úo incremental conclu├¡da: {connections_processed} conex├╡es processadas")
            print(f"   ≡ƒÆ│ Contas: {accounts_inserted} novas, {accounts_updated} atualizadas, {accounts_unchanged} inalteradas")
            print(f"   ≡ƒÆ░ Transa├º├╡es: {transactions_inserted} novas, {transactions_updated} atualizadas, {transactions_unchanged} inalteradas")
            if conflicts_detected > 0:
                print(f"   ΓÜá∩╕Å Conflitos: {conflicts_detected} transa├º├╡es com conflitos detectados")
            
            return True
            
        except Exception as e:
            print(f"Γ¥î Erro na sincroniza├º├úo incremental: {e}")
            return False

    def save_sync_data_incremental_with_stats(self, item_id: str, accounts: List[Dict], transactions: List[Dict]) -> Dict:
        """Salva dados de sincroniza├º├úo de forma incremental e retorna estat├¡sticas detalhadas"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Usar hor├írio de Bras├¡lia
            current_timestamp = get_brasilia_time()
            
            # Registra a sincroniza├º├úo
            cursor.execute('''
                INSERT INTO sync_history (item_id, accounts_count, transactions_count, modification_date)
                VALUES (?, ?, ?, ?)
            ''', (item_id, len(accounts), len(transactions), current_timestamp))
            
            # Estat├¡sticas para retorno
            stats = {
                'accounts_inserted': 0,
                'accounts_updated': 0,
                'accounts_unchanged': 0,
                'transactions_inserted': 0,
                'transactions_updated': 0,
                'transactions_unchanged': 0
            }
            
            # -------------------------------------------------------------
            # OTIMIZAÇÃO: Pré-carrega contas e transações existentes
            # -------------------------------------------------------------
            account_ids = [a.get('id') for a in accounts if a.get('id')]
            existing_accounts = {}
            if account_ids:
                # Busca todas as contas existentes de uma vez
                placeholders = ','.join('?' * len(account_ids))
                cursor.execute(f'SELECT id, name, balance, currency_code FROM accounts WHERE id IN ({placeholders})', account_ids)
                for row in cursor.fetchall():
                    existing_accounts[row[0]] = {
                        'name': row[1],
                        'balance': row[2],
                        'currency_code': row[3]
                    }

            # Processa contas incrementalmente
            for account in accounts:
                account_id = account.get('id')
                if not account_id:
                    continue
                existing = existing_accounts.get(account_id)
                new_name = account.get('name')
                new_balance = account.get('balance', 0)
                new_currency = account.get('currencyCode', 'BRL')
                if existing:
                    has_changes = (
                        existing['name'] != new_name or
                        abs((existing['balance'] or 0) - new_balance) > 0.01 or
                        existing['currency_code'] != new_currency
                    )
                    if has_changes:
                        cursor.execute('''
                            UPDATE accounts
                            SET name=?, type=?, subtype=?, balance=?, currency_code=?,
                                item_id=?, connection_name=?, modification_date=?
                            WHERE id=?
                        ''', (
                            new_name, account.get('type'), account.get('subtype'), new_balance, new_currency,
                            account.get('item_id', item_id),  # Usa item_id da conta se existir
                            account.get('connection_name', 'N/A'), current_timestamp, account_id
                        ))
                        stats['accounts_updated'] += 1
                    else:
                        stats['accounts_unchanged'] += 1
                else:
                    cursor.execute('''
                        INSERT INTO accounts
                        (id, name, type, subtype, balance, currency_code, item_id, connection_name, creation_date, modification_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        account_id, new_name, account.get('type'), account.get('subtype'), new_balance, new_currency,
                        account.get('item_id', item_id), account.get('connection_name', 'N/A'), current_timestamp, current_timestamp
                    ))
                    stats['accounts_inserted'] += 1

            # Pré-carrega transações existentes em lotes para reduzir SELECT por transação
            transaction_ids = [t.get('id') for t in transactions if t.get('id')]
            existing_transactions = {}
            if transaction_ids:
                # SQLite limite de 999 parâmetros por instrução - processa em chunks
                for i in range(0, len(transaction_ids), 900):
                    chunk = transaction_ids[i:i+900]
                    placeholders = ','.join('?' * len(chunk))
                    cursor.execute(
                        f'SELECT id, amount, description, transaction_date, verified, type, category FROM transactions WHERE id IN ({placeholders})',
                        chunk
                    )
                    for row in cursor.fetchall():
                        existing_transactions[row[0]] = {
                            'amount': row[1],
                            'description': row[2],
                            'transaction_date': row[3],
                            'verified': row[4],
                            'type': row[5],
                            'category': row[6]
                        }

            for transaction in transactions:
                transaction_id = transaction.get('id')
                if not transaction_id:
                    continue
                existing = existing_transactions.get(transaction_id)
                new_amount = abs(transaction.get('amount', 0) or 0)
                new_description = transaction.get('description')
                new_date_raw = transaction.get('date')
                new_type = transaction.get('type')
                new_category = transaction.get('category')
                # Converte data apenas uma vez
                new_date_converted = convert_iso_to_standard_format(new_date_raw)

                if existing:
                    is_verified = existing.get('verified', 0)
                    existing_amount = existing.get('amount', 0)
                    existing_description = existing.get('description')
                    existing_date = existing.get('transaction_date')
                    existing_type = existing.get('type')
                    existing_category = existing.get('category')

                    existing_date_normalized = normalize_date_for_comparison(existing_date)
                    new_date_normalized = normalize_date_for_comparison(new_date_converted)

                    if is_verified:
                        has_conflicts = (
                            abs(existing_amount - new_amount) > 0.01 or
                            existing_description != new_description or
                            existing_date_normalized != new_date_normalized or
                            existing_type != new_type or
                            existing_category != new_category
                        )
                        if has_conflicts:
                            conflict_log = generate_conflict_log(
                                {
                                    'amount': existing_amount,
                                    'description': existing_description,
                                    'date': existing_date,
                                    'type': existing_type,
                                    'category': existing_category
                                },
                                {
                                    'amount': new_amount,
                                    'description': new_description,
                                    'date': new_date_converted,
                                    'type': new_type,
                                    'category': new_category
                                }
                            )
                            cursor.execute('''
                                UPDATE transactions
                                SET conflict_detected = 1, conflict_log = ?
                                WHERE id = ?
                            ''', (conflict_log, transaction_id))
                            stats['conflicts_detected'] = stats.get('conflicts_detected', 0) + 1
                        stats['transactions_unchanged'] += 1
                        continue

                    # Não verificada - verifica mudanças
                    has_changes = (
                        abs(existing_amount - new_amount) > 0.01 or
                        existing_description != new_description or
                        existing_date_normalized != new_date_normalized or
                        existing_type != new_type or
                        existing_category != new_category
                    )
                    if has_changes:
                        cursor.execute('''
                            UPDATE transactions
                            SET account_id=?, account_name=?, amount=?, description=?, transaction_date=?,
                                category=?, type=?, item_id=?, connection_name=?, modification_date=?,
                                conflict_detected=0, manual_modification=0
                            WHERE id=?
                        ''', (
                            transaction.get('accountId'), transaction.get('account_name'), new_amount, new_description,
                            new_date_converted, new_category, new_type,
                            transaction.get('item_id', item_id), transaction.get('connection_name', 'N/A'),
                            current_timestamp, transaction_id
                        ))
                        stats['transactions_updated'] += 1
                    else:
                        stats['transactions_unchanged'] += 1
                else:
                    cursor.execute('''
                        INSERT INTO transactions
                        (id, account_id, account_name, amount, description, transaction_date, category, type, item_id, connection_name, creation_date, modification_date, manual_modification)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                    ''', (
                        transaction_id, transaction.get('accountId'), transaction.get('account_name'), new_amount,
                        new_description, new_date_converted, new_category, new_type,
                        transaction.get('item_id', item_id), transaction.get('connection_name', 'N/A'),
                        current_timestamp, current_timestamp
                    ))
                    stats['transactions_inserted'] += 1
            
            conn.commit()
            conn.close()
            
            # Log detalhado da sincroniza├º├úo incremental
            connections_processed = len(set(t.get('connection_name', 'N/A') for t in transactions)) if transactions else 0
            print(f"≡ƒôè Sincroniza├º├úo incremental conclu├¡da: {connections_processed} conex├╡es processadas")
            print(f"   ≡ƒÆ│ Contas: {stats['accounts_inserted']} novas, {stats['accounts_updated']} atualizadas, {stats['accounts_unchanged']} inalteradas")
            print(f"   ≡ƒÆ░ Transa├º├╡es: {stats['transactions_inserted']} novas, {stats['transactions_updated']} atualizadas, {stats['transactions_unchanged']} inalteradas")
            if stats.get('conflicts_detected', 0) > 0:
                print(f"   ΓÜá∩╕Å Conflitos: {stats['conflicts_detected']} transa├º├╡es com conflitos detectados")
            
            return {
                'success': True,
                'stats': stats,
                'message': 'Sincroniza├º├úo incremental conclu├¡da com sucesso'
            }
            
        except Exception as e:
            print(f"Γ¥î Erro na sincroniza├º├úo incremental: {e}")
            return {
                'success': False,
                'message': f'Erro na sincroniza├º├úo: {e}',
                'stats': {}
            }

    def update_transaction_verification(self, transaction_id: str, verified_status: int) -> bool:
        """
        Atualiza o status de verifica├º├úo de uma transa├º├úo
        """
        conn = None
        cursor = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            brasilia_time = get_brasilia_time()
            
            cursor.execute('''
                UPDATE transactions 
                SET verified = ?, modification_date = ?
                WHERE id = ?
            ''', (verified_status, brasilia_time, transaction_id))
            
            conn.commit()
            return cursor.rowcount > 0
            
        except sqlite3.Error as e:
            print(f"Erro ao atualizar verificação da transação: {e}")
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def update_transaction_ignore_status(self, transaction_id: str, ignore_status: int) -> bool:
        """
        Atualiza o status de ignorar de uma transação
        """
        conn = None
        cursor = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            brasilia_time = get_brasilia_time()
            
            cursor.execute('''
                UPDATE transactions 
                SET ignorar_transacao = ?, modification_date = ?
                WHERE id = ?
            ''', (ignore_status, brasilia_time, transaction_id))
            
            conn.commit()
            return cursor.rowcount > 0
            
        except sqlite3.Error as e:
            print(f"Erro ao atualizar status de ignorar da transação: {e}")
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    # ========================================
    # MÉTODOS PARA GERENCIAMENTO DE CONTAS MANUAIS
    # ========================================
    
    def create_manual_account(self, name: str, account_type: str, subtype: str = None, 
                            balance: float = 0.0, currency_code: str = 'BRL') -> str:
        """Cria uma nova conta manual"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Gerar ID único para conta manual
            account_id = f"manual_{uuid.uuid4().hex[:12]}"
            
            # Usar horário de Brasília para timestamps
            current_timestamp = get_brasilia_time()
            
            cursor.execute('''
                INSERT INTO accounts 
                (id, name, type, subtype, balance, currency_code, 
                 last_updated, creation_date, modification_date,
                 connection_name, item_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)
            ''', (account_id, name, account_type, subtype, balance, currency_code,
                  current_timestamp, current_timestamp, current_timestamp))
            
            conn.commit()
            print(f"✅ Conta manual criada: {name} (ID: {account_id})")
            return account_id
            
        except sqlite3.Error as e:
            print(f"❌ Erro ao criar conta manual: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def update_manual_account(self, account_id: str, **kwargs) -> bool:
        """Atualiza uma conta manual"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Verificar se é conta manual
            cursor.execute('''
                SELECT id FROM accounts 
                WHERE id = ? AND (connection_name IS NULL OR connection_name = '')
            ''', (account_id,))
            
            if not cursor.fetchone():
                print(f"❌ Conta {account_id} não encontrada ou não é manual")
                return False
            
            # Construir query de atualização dinamicamente
            allowed_fields = ['name', 'type', 'subtype', 'balance', 'currency_code']
            updates = []
            values = []
            
            for field, value in kwargs.items():
                if field in allowed_fields:
                    updates.append(f"{field} = ?")
                    values.append(value)
            
            if not updates:
                print("❌ Nenhum campo válido para atualizar")
                return False
            
            # Adicionar timestamp de modificação
            updates.append("modification_date = ?")
            values.append(get_brasilia_time())
            values.append(account_id)
            
            query = f"UPDATE accounts SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, values)
            
            conn.commit()
            
            if cursor.rowcount > 0:
                print(f"✅ Conta manual atualizada: {account_id}")
                return True
            else:
                print(f"❌ Nenhuma conta foi atualizada")
                return False
            
        except sqlite3.Error as e:
            print(f"❌ Erro ao atualizar conta manual: {e}")
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def delete_manual_account_with_transactions(self, account_id: str) -> tuple[bool, str]:
        """Exclui uma conta manual e todas as suas transações"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Verificar se é conta manual
            cursor.execute('''
                SELECT name FROM accounts 
                WHERE id = ? AND (connection_name IS NULL OR connection_name = '')
            ''', (account_id,))
            
            account = cursor.fetchone()
            if not account:
                return False, f"Conta {account_id} não encontrada ou não é manual"
            
            account_name = account[0]
            
            # Contar transações associadas
            cursor.execute('''
                SELECT COUNT(*) FROM transactions WHERE account_id = ?
            ''', (account_id,))
            
            transaction_count = cursor.fetchone()[0]
            
            # Excluir transações primeiro (se houver)
            if transaction_count > 0:
                cursor.execute('DELETE FROM transactions WHERE account_id = ?', (account_id,))
                print(f"✅ {transaction_count} transação(ões) excluída(s) da conta {account_name}")
            
            # Excluir a conta
            cursor.execute('DELETE FROM accounts WHERE id = ?', (account_id,))
            conn.commit()
            
            if cursor.rowcount > 0:
                if transaction_count > 0:
                    message = f"Conta '{account_name}' e {transaction_count} transação(ões) foram excluídas com sucesso!"
                else:
                    message = f"Conta '{account_name}' foi excluída com sucesso!"
                
                print(f"✅ {message}")
                return True, message
            else:
                return False, "Nenhuma conta foi excluída"
            
        except sqlite3.Error as e:
            print(f"❌ Erro ao excluir conta manual: {e}")
            return False, f"Erro ao excluir conta: {e}"
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def get_account_transaction_count(self, account_id: str) -> int:
        """Obtém a contagem de transações de uma conta"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT COUNT(*) FROM transactions WHERE account_id = ?
            ''', (account_id,))
            
            count = cursor.fetchone()[0]
            return count
            
        except sqlite3.Error as e:
            print(f"❌ Erro ao contar transações: {e}")
            return 0
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def delete_manual_account(self, account_id: str) -> bool:
        """Exclui uma conta manual (apenas se não houver transações)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Verificar se é conta manual
            cursor.execute('''
                SELECT name FROM accounts 
                WHERE id = ? AND (connection_name IS NULL OR connection_name = '')
            ''', (account_id,))
            
            account = cursor.fetchone()
            if not account:
                print(f"❌ Conta {account_id} não encontrada ou não é manual")
                return False
            
            # Verificar se há transações associadas
            cursor.execute('''
                SELECT COUNT(*) FROM transactions WHERE account_id = ?
            ''', (account_id,))
            
            transaction_count = cursor.fetchone()[0]
            if transaction_count > 0:
                print(f"❌ Não é possível excluir conta {account[0]} - possui {transaction_count} transações")
                return False
            
            # Excluir a conta
            cursor.execute('DELETE FROM accounts WHERE id = ?', (account_id,))
            conn.commit()
            
            if cursor.rowcount > 0:
                print(f"✅ Conta manual excluída: {account[0]}")
                return True
            else:
                print(f"❌ Nenhuma conta foi excluída")
                return False
            
        except sqlite3.Error as e:
            print(f"❌ Erro ao excluir conta manual: {e}")
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def get_account_by_id(self, account_id: str) -> Dict:
        """Obtém uma conta específica por ID"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, name, type, subtype, balance, currency_code, last_updated,
                       creation_date, modification_date, connection_name, item_id
                FROM accounts 
                WHERE id = ?
            ''', (account_id,))
            
            row = cursor.fetchone()
            if row:
                is_manual = row[9] is None or row[9] == '' or row[10] is None or row[10] == ''
                
                return {
                    'id': row[0],
                    'name': row[1],
                    'type': row[2],
                    'subtype': row[3],
                    'balance': row[4],
                    'currency_code': row[5],
                    'last_updated': row[6],
                    'creation_date': row[7],
                    'modification_date': row[8],
                    'connection_name': row[9],
                    'item_id': row[10],
                    'is_manual': is_manual,
                    'source_type': 'Manual' if is_manual else 'Conexão'
                }
            
            return None
            
        except sqlite3.Error as e:
            print(f"❌ Erro ao buscar conta: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def get_account_types(self) -> List[str]:
        """Obtém lista de tipos de conta únicos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT DISTINCT type FROM accounts 
                WHERE type IS NOT NULL AND type != ''
                ORDER BY type
            ''')
            
            return [row[0] for row in cursor.fetchall()]
            
        except sqlite3.Error as e:
            print(f"❌ Erro ao buscar tipos de conta: {e}")
            return []
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def create_manual_transaction(self, account_id: str, amount: float, description: str, 
                                transaction_date: str, category: str = None, 
                                transaction_type: str = None) -> str:
        """
        Cria uma nova transação manual
        
        Args:
            account_id: ID da conta
            amount: Valor da transação (positivo para entrada, negativo para saída)
            description: Descrição da transação
            transaction_date: Data da transação (YYYY-MM-DD HH:MM:SS)
            category: Categoria opcional
            transaction_type: Tipo da transação (CREDIT ou DEBIT)
            
        Returns:
            ID da transação criada ou None se erro
        """
        try:
            # Gerar ID único para transação manual
            transaction_id = f"manual_{uuid.uuid4().hex[:12]}"
            
            # Determinar tipo se não fornecido (com base no sinal original informado)
            if not transaction_type:
                transaction_type = "CREDIT" if amount >= 0 else "DEBIT"

            # NOVO PADRÃO: armazenar sempre valor absoluto; direção no campo type
            amount = abs(amount)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Inserir transação
            cursor.execute('''
                INSERT INTO transactions (
                    id, account_id, amount, description, transaction_date, 
                    category, type, item_id, connection_name, verified, 
                    ignorar_transacao, manual_modification, creation_date, modification_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (
                transaction_id,
                account_id,
                amount,
                description,
                transaction_date,
                category,
                transaction_type,
                'manual',
                'MANUAL',
                0,  # verified = False
                0,  # ignorar_transacao = False
                1   # manual_modification = True (transação criada manualmente)
            ))
            
            conn.commit()
            print(f"✅ Transação manual criada: {description} (ID: {transaction_id})")
            
            return transaction_id
            
        except sqlite3.Error as e:
            print(f"❌ Erro ao criar transação manual: {e}")
            return None
        except Exception as e:
            print(f"❌ Erro geral ao criar transação manual: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def delete_transaction(self, transaction_id: str) -> tuple[bool, str]:
        """
        Exclui uma transação
        
        Args:
            transaction_id: ID da transação a ser excluída
            
        Returns:
            Tupla (sucesso: bool, mensagem: str)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Verificar se a transação existe
            cursor.execute('SELECT description FROM transactions WHERE id = ?', (transaction_id,))
            transaction = cursor.fetchone()
            
            if not transaction:
                return False, "Transação não encontrada"
            
            description = transaction[0]
            
            # Excluir a transação
            cursor.execute('DELETE FROM transactions WHERE id = ?', (transaction_id,))
            
            if cursor.rowcount == 0:
                return False, "Nenhuma transação foi excluída"
            
            conn.commit()
            print(f"✅ Transação '{description}' foi excluída com sucesso!")
            
            return True, f"Transação '{description}' foi excluída com sucesso!"
            
        except sqlite3.Error as e:
            error_msg = f"Erro ao excluir transação: {e}"
            print(f"❌ {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"Erro geral ao excluir transação: {e}"
            print(f"❌ {error_msg}")
            return False, error_msg
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    # ========================================
    # MÉTODOS PARA GERENCIAR CATEGORIAS
    # ========================================
    
    def get_user_categories(self, transaction_type: str = None, active_only: bool = True) -> List[Dict]:
        """
        Busca categorias criadas pelo usuário
        
        Args:
            transaction_type: 'CREDIT', 'DEBIT' ou None para todas
            active_only: Se deve retornar apenas categorias ativas
            
        Returns:
            Lista de categorias com suas subcategorias
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = '''
                SELECT id, name, subcategory, transaction_type, description, 
                       color, icon, is_active, creation_date, modification_date
                FROM user_categories
                WHERE 1=1
            '''
            params = []
            
            if transaction_type:
                query += ' AND transaction_type = ?'
                params.append(transaction_type)
            
            if active_only:
                query += ' AND is_active = 1'
            
            query += ' ORDER BY name, subcategory'
            
            cursor.execute(query, params)
            categories = []
            
            for row in cursor.fetchall():
                categories.append({
                    'id': row[0],
                    'name': row[1],
                    'subcategory': row[2],
                    'transaction_type': row[3],
                    'description': row[4],
                    'color': row[5],
                    'icon': row[6],
                    'is_active': row[7],
                    'creation_date': row[8],
                    'modification_date': row[9]
                })
            
            conn.close()
            return categories
            
        except Exception as e:
            print(f"❌ Erro ao buscar categorias: {e}")
            return []
    
    def create_user_category(self, name: str, transaction_type: str, subcategory: str = None, 
                           description: str = None, color: str = None, icon: str = None) -> int:
        """
        Cria uma nova categoria/subcategoria
        
        Args:
            name: Nome da categoria
            transaction_type: 'CREDIT' ou 'DEBIT'
            subcategory: Nome da subcategoria (opcional)
            description: Descrição da categoria
            color: Cor da categoria (hex)
            icon: Ícone da categoria (FontAwesome)
            
        Returns:
            ID da categoria criada ou None se houver erro
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            current_timestamp = get_brasilia_time()
            
            cursor.execute('''
                INSERT INTO user_categories 
                (name, subcategory, transaction_type, description, color, icon, creation_date, modification_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                name.strip(),
                subcategory.strip() if subcategory else None,
                transaction_type,
                description.strip() if description else None,
                color,
                icon,
                current_timestamp,
                current_timestamp
            ))
            
            category_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            print(f"✅ Categoria criada: {name}" + (f" > {subcategory}" if subcategory else ""))
            return category_id
            
        except sqlite3.IntegrityError as e:
            print(f"❌ Categoria já existe: {name}" + (f" > {subcategory}" if subcategory else ""))
            return None
        except Exception as e:
            print(f"❌ Erro ao criar categoria: {e}")
            return None
    
    def update_user_category(self, category_id: int, **kwargs) -> bool:
        """
        Atualiza uma categoria existente
        
        Args:
            category_id: ID da categoria
            **kwargs: Campos a serem atualizados
            
        Returns:
            True se atualizado com sucesso
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Campos permitidos para atualização
            allowed_fields = ['name', 'subcategory', 'transaction_type', 'description', 'color', 'icon', 'is_active']
            
            set_clauses = []
            params = []
            
            for key, value in kwargs.items():
                if key in allowed_fields:
                    set_clauses.append(f"{key} = ?")
                    params.append(value)
            
            if not set_clauses:
                return False
            
            # Adiciona atualização da data de modificação
            set_clauses.append("modification_date = ?")
            params.append(get_brasilia_time())
            params.append(category_id)
            
            query = f"UPDATE user_categories SET {', '.join(set_clauses)} WHERE id = ?"
            cursor.execute(query, params)
            
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            
            return success
            
        except Exception as e:
            print(f"❌ Erro ao atualizar categoria: {e}")
            return False
    
    def delete_user_category(self, category_id: int) -> tuple[bool, str]:
        """
        Exclui uma categoria
        
        Args:
            category_id: ID da categoria
            
        Returns:
            Tupla (sucesso: bool, mensagem: str)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Verificar se a categoria existe
            cursor.execute('SELECT name, subcategory FROM user_categories WHERE id = ?', (category_id,))
            category = cursor.fetchone()
            
            if not category:
                return False, "Categoria não encontrada"
            
            name = category[0]
            subcategory = category[1]
            category_display = name + (f" > {subcategory}" if subcategory else "")
            
            # Excluir a categoria
            cursor.execute('DELETE FROM user_categories WHERE id = ?', (category_id,))
            
            if cursor.rowcount == 0:
                return False, "Nenhuma categoria foi excluída"
            
            conn.commit()
            conn.close()
            
            print(f"✅ Categoria '{category_display}' foi excluída com sucesso!")
            return True, f"Categoria '{category_display}' foi excluída com sucesso!"
            
        except Exception as e:
            error_msg = f"Erro ao excluir categoria: {e}"
            print(f"❌ {error_msg}")
            return False, error_msg
    
    def get_categories_grouped(self, transaction_type: str = None) -> Dict:
        """
        Retorna categorias agrupadas por nome principal
        
        Args:
            transaction_type: 'CREDIT', 'DEBIT' ou None para todas
            
        Returns:
            Dicionário com categorias agrupadas
        """
        try:
            categories = self.get_user_categories(transaction_type)
            grouped = {}
            
            for category in categories:
                main_category = category['name']
                if main_category not in grouped:
                    grouped[main_category] = {
                        'id': category['id'],
                        'name': main_category,
                        'transaction_type': category['transaction_type'],
                        'description': category['description'],
                        'color': category['color'],
                        'icon': category['icon'],
                        'subcategories': []
                    }
                
                if category['subcategory']:
                    grouped[main_category]['subcategories'].append({
                        'id': category['id'],
                        'name': category['subcategory'],
                        'description': category['description'],
                        'color': category['color'],
                        'icon': category['icon']
                    })
            
            return grouped
            
        except Exception as e:
            print(f"❌ Erro ao agrupar categorias: {e}")
            return {}
    
    def populate_default_categories(self) -> bool:
        """
        Popula categorias padrão no banco de dados se não existirem
        
        Returns:
            True se categorias foram criadas com sucesso
        """
        try:
            # Verificar se já existem categorias
            existing_categories = self.get_user_categories()
            if existing_categories:
                print("📋 Categorias já existem no banco de dados")
                return True
            
            print("📋 Criando categorias padrão...")
            
            # Categorias de ENTRADA (CREDIT)
            credit_categories = [
                # Categorias principais de entrada
                {'name': 'Salário', 'subcategory': None, 'description': 'Salário e remuneração', 'color': '#28a745', 'icon': 'fas fa-money-bill-wave'},
                {'name': 'Freelance', 'subcategory': None, 'description': 'Trabalhos freelance e consultoria', 'color': '#17a2b8', 'icon': 'fas fa-laptop'},
                {'name': 'Investimentos', 'subcategory': None, 'description': 'Rendimentos de investimentos', 'color': '#ffc107', 'icon': 'fas fa-chart-line'},
                {'name': 'Vendas', 'subcategory': None, 'description': 'Vendas de produtos ou serviços', 'color': '#6f42c1', 'icon': 'fas fa-shopping-cart'},
                {'name': 'Outros', 'subcategory': None, 'description': 'Outras receitas', 'color': '#6c757d', 'icon': 'fas fa-plus-circle'},
                
                # Subcategorias de Investimentos
                {'name': 'Investimentos', 'subcategory': 'Dividendos', 'description': 'Dividendos de ações', 'color': '#ffc107', 'icon': 'fas fa-percentage'},
                {'name': 'Investimentos', 'subcategory': 'Rendimento CDB', 'description': 'Rendimentos de CDB', 'color': '#ffc107', 'icon': 'fas fa-university'},
                {'name': 'Investimentos', 'subcategory': 'Tesouro Direto', 'description': 'Rendimentos do Tesouro', 'color': '#ffc107', 'icon': 'fas fa-landmark'},
                
                # Subcategorias de Outros
                {'name': 'Outros', 'subcategory': 'Presente/Doação', 'description': 'Presentes recebidos', 'color': '#6c757d', 'icon': 'fas fa-gift'},
                {'name': 'Outros', 'subcategory': 'Reembolso', 'description': 'Reembolsos diversos', 'color': '#6c757d', 'icon': 'fas fa-undo'},
            ]
            
            # Categorias de SAÍDA (DEBIT)
            debit_categories = [
                # Categorias principais de saída
                {'name': 'Alimentação', 'subcategory': None, 'description': 'Gastos com alimentação', 'color': '#fd7e14', 'icon': 'fas fa-utensils'},
                {'name': 'Transporte', 'subcategory': None, 'description': 'Gastos com transporte', 'color': '#20c997', 'icon': 'fas fa-car'},
                {'name': 'Moradia', 'subcategory': None, 'description': 'Gastos com moradia', 'color': '#e83e8c', 'icon': 'fas fa-home'},
                {'name': 'Saúde', 'subcategory': None, 'description': 'Gastos com saúde', 'color': '#dc3545', 'icon': 'fas fa-heart'},
                {'name': 'Educação', 'subcategory': None, 'description': 'Gastos com educação', 'color': '#6f42c1', 'icon': 'fas fa-graduation-cap'},
                {'name': 'Lazer', 'subcategory': None, 'description': 'Entretenimento e lazer', 'color': '#17a2b8', 'icon': 'fas fa-gamepad'},
                {'name': 'Compras', 'subcategory': None, 'description': 'Compras diversas', 'color': '#ffc107', 'icon': 'fas fa-shopping-bag'},
                {'name': 'Serviços', 'subcategory': None, 'description': 'Serviços diversos', 'color': '#6c757d', 'icon': 'fas fa-tools'},
                {'name': 'Outros', 'subcategory': None, 'description': 'Outras despesas', 'color': '#495057', 'icon': 'fas fa-minus-circle'},
                
                # Subcategorias de Alimentação
                {'name': 'Alimentação', 'subcategory': 'Supermercado', 'description': 'Compras no supermercado', 'color': '#fd7e14', 'icon': 'fas fa-shopping-cart'},
                {'name': 'Alimentação', 'subcategory': 'Restaurante', 'description': 'Refeições em restaurantes', 'color': '#fd7e14', 'icon': 'fas fa-store'},
                {'name': 'Alimentação', 'subcategory': 'Delivery', 'description': 'Pedidos de comida', 'color': '#fd7e14', 'icon': 'fas fa-motorcycle'},
                {'name': 'Alimentação', 'subcategory': 'Lanche', 'description': 'Lanches e petiscos', 'color': '#fd7e14', 'icon': 'fas fa-cookie-bite'},
                
                # Subcategorias de Transporte
                {'name': 'Transporte', 'subcategory': 'Combustível', 'description': 'Gasolina e combustível', 'color': '#20c997', 'icon': 'fas fa-gas-pump'},
                {'name': 'Transporte', 'subcategory': 'Uber/Taxi', 'description': 'Corridas de aplicativo', 'color': '#20c997', 'icon': 'fas fa-taxi'},
                {'name': 'Transporte', 'subcategory': 'Transporte Público', 'description': 'Ônibus, metrô, trem', 'color': '#20c997', 'icon': 'fas fa-bus'},
                {'name': 'Transporte', 'subcategory': 'Manutenção', 'description': 'Manutenção do veículo', 'color': '#20c997', 'icon': 'fas fa-wrench'},
                
                # Subcategorias de Moradia
                {'name': 'Moradia', 'subcategory': 'Aluguel', 'description': 'Aluguel da casa/apartamento', 'color': '#e83e8c', 'icon': 'fas fa-key'},
                {'name': 'Moradia', 'subcategory': 'Condomínio', 'description': 'Taxa de condomínio', 'color': '#e83e8c', 'icon': 'fas fa-building'},
                {'name': 'Moradia', 'subcategory': 'Energia', 'description': 'Conta de luz', 'color': '#e83e8c', 'icon': 'fas fa-bolt'},
                {'name': 'Moradia', 'subcategory': 'Água', 'description': 'Conta de água', 'color': '#e83e8c', 'icon': 'fas fa-tint'},
                {'name': 'Moradia', 'subcategory': 'Internet', 'description': 'Internet e telefone', 'color': '#e83e8c', 'icon': 'fas fa-wifi'},
                {'name': 'Moradia', 'subcategory': 'Móveis', 'description': 'Móveis e decoração', 'color': '#e83e8c', 'icon': 'fas fa-couch'},
                
                # Subcategorias de Saúde
                {'name': 'Saúde', 'subcategory': 'Médico', 'description': 'Consultas médicas', 'color': '#dc3545', 'icon': 'fas fa-user-md'},
                {'name': 'Saúde', 'subcategory': 'Farmácia', 'description': 'Medicamentos', 'color': '#dc3545', 'icon': 'fas fa-pills'},
                {'name': 'Saúde', 'subcategory': 'Plano de Saúde', 'description': 'Mensalidade do plano', 'color': '#dc3545', 'icon': 'fas fa-heartbeat'},
                {'name': 'Saúde', 'subcategory': 'Dentista', 'description': 'Tratamentos dentários', 'color': '#dc3545', 'icon': 'fas fa-tooth'},
                
                # Subcategorias de Lazer
                {'name': 'Lazer', 'subcategory': 'Cinema', 'description': 'Cinema e filmes', 'color': '#17a2b8', 'icon': 'fas fa-film'},
                {'name': 'Lazer', 'subcategory': 'Viagem', 'description': 'Viagens e turismo', 'color': '#17a2b8', 'icon': 'fas fa-plane'},
                {'name': 'Lazer', 'subcategory': 'Academia', 'description': 'Academia e exercícios', 'color': '#17a2b8', 'icon': 'fas fa-dumbbell'},
                {'name': 'Lazer', 'subcategory': 'Streaming', 'description': 'Netflix, Spotify, etc.', 'color': '#17a2b8', 'icon': 'fas fa-play'},
                
                # Subcategorias de Compras
                {'name': 'Compras', 'subcategory': 'Roupas', 'description': 'Roupas e acessórios', 'color': '#ffc107', 'icon': 'fas fa-tshirt'},
                {'name': 'Compras', 'subcategory': 'Eletrônicos', 'description': 'Eletrônicos e gadgets', 'color': '#ffc107', 'icon': 'fas fa-mobile-alt'},
                {'name': 'Compras', 'subcategory': 'Livros', 'description': 'Livros e revistas', 'color': '#ffc107', 'icon': 'fas fa-book'},
                {'name': 'Compras', 'subcategory': 'Presentes', 'description': 'Presentes para terceiros', 'color': '#ffc107', 'icon': 'fas fa-gift'},
                
                # Subcategorias de Serviços
                {'name': 'Serviços', 'subcategory': 'Bancários', 'description': 'Taxas bancárias', 'color': '#6c757d', 'icon': 'fas fa-university'},
                {'name': 'Serviços', 'subcategory': 'Beleza', 'description': 'Cabelereiro, estética', 'color': '#6c757d', 'icon': 'fas fa-cut'},
                {'name': 'Serviços', 'subcategory': 'Advocacia', 'description': 'Serviços advocatícios', 'color': '#6c757d', 'icon': 'fas fa-gavel'},
                {'name': 'Serviços', 'subcategory': 'Contabilidade', 'description': 'Serviços contábeis', 'color': '#6c757d', 'icon': 'fas fa-calculator'},
            ]
            
            # Criar categorias de entrada
            for category in credit_categories:
                self.create_user_category(
                    name=category['name'],
                    subcategory=category['subcategory'],
                    transaction_type='CREDIT',
                    description=category['description'],
                    color=category['color'],
                    icon=category['icon']
                )
            
            # Criar categorias de saída
            for category in debit_categories:
                self.create_user_category(
                    name=category['name'],
                    subcategory=category['subcategory'],
                    transaction_type='DEBIT',
                    description=category['description'],
                    color=category['color'],
                    icon=category['icon']
                )
            
            print(f"✅ Criadas {len(credit_categories)} categorias de entrada e {len(debit_categories)} categorias de saída")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao criar categorias padrão: {e}")
            return False

    def update_transaction_category(self, transaction_id: str, user_category: str = None, user_subcategory: str = None) -> bool:
        """Atualiza as categorias de usuário de uma transação sem marcar como modificação manual.

        Observações:
        - Não altera o campo manual_modification.
        - Atualiza modification_date usando horário de Brasília (YYYY-MM-DD HH:MM:SS).
        - Mantém valores existentes quando o parâmetro correspondente é None (atualização parcial).
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Usar horário de Brasília conforme padrão do projeto
            current_timestamp = get_brasilia_time()

            # Atualiza apenas os campos informados; mantém os demais (COALESCE com valor atual)
            cursor.execute('''
                UPDATE transactions 
                SET 
                    user_category = COALESCE(?, user_category), 
                    user_subcategory = COALESCE(?, user_subcategory), 
                    modification_date = ?
                WHERE id = ?
            ''', (user_category, user_subcategory, current_timestamp, transaction_id))

            conn.commit()
            rows_affected = cursor.rowcount
            conn.close()

            return rows_affected > 0

        except Exception as e:
            print(f"❌ Erro ao atualizar categoria da transação: {e}")
            return False

    # ==========================
    #  DIVISÃO - PERCENTUAIS
    # ==========================
    def update_transaction_split(self, transaction_id: str, user1_percent: float, user2_percent: float | None = None) -> bool:
        """Atualiza os percentuais de divisão de uma transação.

        - user2_percent é opcional; se omitido, será 100 - user1_percent.
        - Garante limites 0..100 e que a soma seja 100 (ajuste fino com 2 casas).
        - Atualiza modification_date com horário de Brasília.
        """
        try:
            if not transaction_id:
                return False
            try:
                p1 = float(user1_percent)
            except Exception:
                p1 = 50.0
            p1 = max(0.0, min(100.0, p1))
            p2 = (100.0 - p1) if user2_percent is None else float(user2_percent)
            p2 = max(0.0, min(100.0, p2))
            # Ajuste de soma
            if abs((p1 + p2) - 100.0) > 0.01:
                p2 = round(100.0 - p1, 2)

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            current_timestamp = get_brasilia_time()
            cursor.execute('''
                UPDATE transactions
                SET user1_percent = ?, user2_percent = ?, modification_date = ?
                WHERE id = ?
            ''', (p1, p2, current_timestamp, transaction_id))
            conn.commit()
            updated = cursor.rowcount > 0
            conn.close()
            return updated
        except Exception as e:
            print(f"❌ Erro ao atualizar divisão da transação {transaction_id}: {e}")
            return False

    def get_division_user_names(self) -> Dict:
        """Obtém os nomes configurados para Usuário 1 e Usuário 2."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT user1_name, user2_name FROM division_settings WHERE id = 1')
            row = cursor.fetchone()
            conn.close()
            if not row:
                return {'user1_name': 'Usuário 1', 'user2_name': 'Usuário 2'}
            return {'user1_name': row[0] or 'Usuário 1', 'user2_name': row[1] or 'Usuário 2'}
        except Exception as e:
            print(f"❌ Erro ao obter nomes da divisão: {e}")
            return {'user1_name': 'Usuário 1', 'user2_name': 'Usuário 2'}

    def update_division_user_names(self, user1_name: str, user2_name: str) -> bool:
        """Atualiza os nomes dos usuários da divisão."""
        try:
            user1_name = (user1_name or 'Usuário 1').strip()
            user2_name = (user2_name or 'Usuário 2').strip()
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            current_timestamp = get_brasilia_time()
            cursor.execute('''
                INSERT INTO division_settings (id, user1_name, user2_name, creation_date, modification_date)
                VALUES (1, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    user1_name = excluded.user1_name,
                    user2_name = excluded.user2_name,
                    modification_date = excluded.modification_date
            ''', (user1_name, user2_name, current_timestamp, current_timestamp))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"❌ Erro ao atualizar nomes da divisão: {e}")
            return False

    def get_accounts_with_splits(self) -> List[Dict]:
        """Retorna contas com percentuais de divisão (default 50/50 se não definido)."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT a.id, a.name, a.type, a.subtype, a.balance, a.currency_code,
                       COALESCE(s.user1_percent, 50.0) AS user1_percent,
                       COALESCE(s.user2_percent, 50.0) AS user2_percent
                FROM accounts a
                LEFT JOIN account_splits s ON s.account_id = a.id
                ORDER BY a.name COLLATE NOCASE
            ''')
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"❌ Erro ao obter contas com divisões: {e}")
            return []

    def upsert_account_split(self, account_id: str, user1_percent: float, user2_percent: float | None = None) -> bool:
        """Insere/atualiza percentuais de divisão para uma conta."""
        try:
            if not account_id:
                return False
            # Normaliza e valida
            try:
                p1 = float(user1_percent)
            except Exception:
                p1 = 50.0
            p1 = max(0.0, min(100.0, p1))
            p2 = (100.0 - p1) if user2_percent is None else float(user2_percent)
            p2 = max(0.0, min(100.0, p2))
            # Ajusta pequena diferença de ponto flutuante
            if abs((p1 + p2) - 100.0) > 0.01:
                p2 = round(100.0 - p1, 2)

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            current_timestamp = get_brasilia_time()
            cursor.execute('''
                INSERT INTO account_splits (account_id, user1_percent, user2_percent, creation_date, modification_date)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(account_id) DO UPDATE SET
                    user1_percent = excluded.user1_percent,
                    user2_percent = excluded.user2_percent,
                    modification_date = excluded.modification_date
            ''', (account_id, p1, p2, current_timestamp, current_timestamp))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"❌ Erro ao salvar divisão da conta {account_id}: {e}")
            return False

    # ========================================
    #  MAPEAMENTO DE CATEGORIAS (DE-PARA)
    # ========================================
    def reconcile_category_mappings(self) -> list[dict]:
        """Garante que todas as categorias vindas da API (transactions.category) tenham um registro na tabela de mapeamento.

        Retorna lista de categorias (dict) recém inseridas que ainda precisam de classificação.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT category, type FROM transactions
                WHERE category IS NOT NULL AND category != ''
            ''')
            existing_categories = cursor.fetchall()
            if not existing_categories:
                conn.close()
                return []

            # Buscar já mapeadas
            cursor.execute('SELECT source_category, transaction_type FROM category_mappings')
            mapped = {(row[0], row[1]) for row in cursor.fetchall()}

            new_rows = []
            now_ts = get_brasilia_time()
            for cat, ttype in existing_categories:
                key = (cat, ttype)
                if key not in mapped:
                    cursor.execute('''
                        INSERT INTO category_mappings (source_category, transaction_type, needs_classification, creation_date, modification_date)
                        VALUES (?, ?, 1, ?, ?)
                    ''', (cat, ttype, now_ts, now_ts))
                    new_rows.append({'source_category': cat, 'transaction_type': ttype})
            if new_rows:
                conn.commit()
            conn.close()
            return new_rows
        except Exception as e:
            print(f"❌ Erro ao reconciliar mapeamentos de categorias: {e}")
            return []

    def get_category_mappings(self) -> list[dict]:
        """Retorna todos os mapeamentos de categorias (API -> usuário)."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, source_category, transaction_type, mapped_user_category, mapped_user_subcategory, needs_classification,
                       creation_date, modification_date
                FROM category_mappings
                ORDER BY source_category COLLATE NOCASE
            ''')
            rows = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return rows
        except Exception as e:
            print(f"❌ Erro ao buscar category_mappings: {e}")
            return []

    def update_category_mapping(self, source_category: str, transaction_type: str | None, mapped_user_category: str | None, mapped_user_subcategory: str | None) -> bool:
        """Atualiza (ou cria) mapeamento de uma categoria da API para categoria/subcategoria do usuário.

        Se mapped_user_category for None ou vazio, marca needs_classification=1.
        """
        try:
            if not source_category:
                return False
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            now_ts = get_brasilia_time()
            needs = 0 if (mapped_user_category and mapped_user_category.strip()) else 1
            cursor.execute('''
                INSERT INTO category_mappings (source_category, transaction_type, mapped_user_category, mapped_user_subcategory, needs_classification, creation_date, modification_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_category, transaction_type) DO UPDATE SET
                    mapped_user_category=excluded.mapped_user_category,
                    mapped_user_subcategory=excluded.mapped_user_subcategory,
                    needs_classification=excluded.needs_classification,
                    modification_date=excluded.modification_date
            ''', (source_category, transaction_type, mapped_user_category, mapped_user_subcategory, needs, now_ts, now_ts))
            conn.commit()
            ok = cursor.rowcount > 0
            conn.close()
            return ok
        except Exception as e:
            print(f"❌ Erro ao atualizar category_mapping: {e}")
            return False

    def count_unmapped_categories(self) -> int:
        """Retorna quantidade de categorias de API ainda não classificadas."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM category_mappings WHERE needs_classification = 1')
            count = cursor.fetchone()[0]
            conn.close()
            return count or 0
        except Exception as e:
            print(f"❌ Erro ao contar unmapped categories: {e}")
            return 0

    def delete_category_mapping(self, source_category: str, transaction_type: str | None) -> bool:
        """Remove um mapeamento específico (será recriado em próxima reconciliação se ainda existir em transações)."""
        try:
            if not source_category:
                return False
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            if transaction_type is None or transaction_type == '':
                cursor.execute('DELETE FROM category_mappings WHERE source_category = ? AND (transaction_type IS NULL OR transaction_type = "")', (source_category,))
            else:
                cursor.execute('DELETE FROM category_mappings WHERE source_category = ? AND transaction_type = ?', (source_category, transaction_type))
            conn.commit()
            removed = cursor.rowcount > 0
            conn.close()
            return removed
        except Exception as e:
            print(f"❌ Erro ao deletar category_mapping: {e}")
            return False

    # ========================================
    #  SUGESTÃO AUTOMÁTICA DE CATEGORIAS
    # ========================================
    def suggest_categories_for_transactions(self, similarity_threshold: float = 0.88, persist: bool = False) -> dict:
        """Gera sugestões de categorias para transações NÃO verificadas.

        Quando persist=False (padrão), NÃO salva no banco. Apenas retorna sugestões.
        Quando persist=True, grava user_category/user_subcategory das transações que não possuem categoria ainda.

        Regras de sugestão:
          1. Base em transações verificadas (match normalizado exato ou fuzzy >= similarity_threshold)
             - desempate por maior frequência e depois data mais recente
          2. Fallback mapeamento de-para (API->Usuário) ativo (needs_classification=0)
          3. Pode sobrescrever sugestões anteriores enquanto não verificada.
        """
        try:
            import difflib
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 1. Carrega transações verificadas com categorias de usuário
            cursor.execute('''
                SELECT description, user_category, user_subcategory, modification_date
                FROM transactions
                WHERE verified = 1
                  AND user_category IS NOT NULL AND user_category != ''
                  AND description IS NOT NULL AND description != ''
            ''')
            verified_rows = cursor.fetchall() or []

            def normalize_desc(s: str) -> str:
                if not s:
                    return ''
                s = s.strip().lower()
                return ' '.join(s.split())  # remove múltiplos espaços

            exact_index: dict[str, list[dict]] = {}
            verified_list: list[dict] = []
            for r in verified_rows:
                norm = normalize_desc(r['description'])
                entry = {
                    'norm': norm,
                    'user_category': r['user_category'],
                    'user_subcategory': r['user_subcategory'],
                    'modification_date': r['modification_date'] or ''
                }
                exact_index.setdefault(norm, []).append(entry)
                verified_list.append(entry)

            # 2. Carrega mapeamentos resolvidos
            cursor.execute('''
                SELECT source_category, transaction_type, mapped_user_category, mapped_user_subcategory
                FROM category_mappings
                WHERE mapped_user_category IS NOT NULL AND mapped_user_category != ''
                  AND needs_classification = 0
            ''')
            mapping_rows = cursor.fetchall()
            mapping_index: dict[tuple[str, str | None], tuple[str, str | None]] = {}
            for mr in mapping_rows:
                mapping_index[(mr['source_category'], mr['transaction_type'])] = (
                    mr['mapped_user_category'], mr['mapped_user_subcategory']
                )

            # 3. Carrega transações alvo (não verificadas)
            cursor.execute('''
                SELECT id, description, category, type, user_category, user_subcategory
                FROM transactions
                WHERE (verified = 0 OR verified IS NULL)
                  AND (ignorar_transacao = 0 OR ignorar_transacao IS NULL)
            ''')
            target_rows = cursor.fetchall()

            stats = {
                'total_candidates': len(target_rows),
                'by_description': 0,
                'by_mapping': 0,
                'no_match': 0,
                'suggested': 0,
                'persisted': 0
            }

            suggestions: list[dict] = []
            updates: list[tuple[str, str, str]] = []

            for tr in target_rows:
                tx_id = tr['id']
                desc = tr['description'] or ''
                api_cat = tr['category']
                ttype = tr['type']
                norm_desc = normalize_desc(desc)
                suggested_cat = None
                suggested_sub = None

                # A) Match exato
                candidates = exact_index.get(norm_desc)
                if candidates:
                    freq: dict[tuple[str, str | None], dict] = {}
                    for c in candidates:
                        key = (c['user_category'], c['user_subcategory'])
                        data = freq.setdefault(key, {'count': 0, 'latest': c['modification_date']})
                        data['count'] += 1
                        if c['modification_date'] and (data['latest'] is None or c['modification_date'] > data['latest']):
                            data['latest'] = c['modification_date']
                    best = sorted(freq.items(), key=lambda kv: (-kv[1]['count'], (kv[1]['latest'] or '')))[0]
                    suggested_cat, suggested_sub = best[0]
                    stats['by_description'] += 1
                else:
                    # B) Fuzzy
                    freq: dict[tuple[str, str | None], dict] = {}
                    for c in verified_list:
                        if not c['norm']:
                            continue
                        ratio = difflib.SequenceMatcher(None, norm_desc, c['norm']).ratio()
                        if ratio >= similarity_threshold:
                            key = (c['user_category'], c['user_subcategory'])
                            data = freq.setdefault(key, {'count': 0, 'latest': c['modification_date'], 'max_ratio': ratio})
                            data['count'] += 1
                            if c['modification_date'] and (data['latest'] is None or c['modification_date'] > data['latest']):
                                data['latest'] = c['modification_date']
                            if ratio > data.get('max_ratio', 0):
                                data['max_ratio'] = ratio
                    if freq:
                        best = sorted(freq.items(), key=lambda kv: (-kv[1]['count'], -kv[1]['max_ratio'], (kv[1]['latest'] or '')))[0]
                        suggested_cat, suggested_sub = best[0]
                        stats['by_description'] += 1

                # C) Fallback mapping
                if not suggested_cat and api_cat:
                    specific_key = (api_cat, ttype)
                    generic_key = (api_cat, None)
                    if specific_key in mapping_index:
                        suggested_cat, suggested_sub = mapping_index[specific_key]
                        stats['by_mapping'] += 1
                    elif generic_key in mapping_index:
                        suggested_cat, suggested_sub = mapping_index[generic_key]
                        stats['by_mapping'] += 1

                if suggested_cat:
                    stats['suggested'] += 1
                    source = 'description' if suggested_cat and stats['by_description'] >= stats['by_mapping'] else 'mapping'
                    suggestions.append({
                        'id': tx_id,
                        'suggested_category': suggested_cat,
                        'suggested_subcategory': suggested_sub,
                        'source': source
                    })
                    if persist and (not tr['user_category'] or tr['user_category'] == ''):
                        updates.append((tx_id, suggested_cat, suggested_sub))
                else:
                    stats['no_match'] += 1

            if persist and updates:
                for tx_id, cat, sub in updates:
                    try:
                        cursor.execute('''
                            UPDATE transactions
                            SET user_category = ?, user_subcategory = ?, modification_date = ?
                            WHERE id = ?
                        ''', (cat, sub, get_brasilia_time(), tx_id))
                        stats['persisted'] += 1
                    except Exception as inner_e:
                        print(f"⚠️ Erro ao aplicar sugestão em {tx_id}: {inner_e}")
                conn.commit()

            conn.close()
            return { 'stats': stats, 'suggestions': suggestions }
        except Exception as e:
            print(f"❌ Erro em suggest_categories_for_transactions: {e}")
            return {
                'stats': {
                    'total_candidates': 0,
                    'by_description': 0,
                    'by_mapping': 0,
                    'no_match': 0,
                    'suggested': 0,
                    'persisted': 0
                },
                'suggestions': [],
                'error': str(e)
            }
