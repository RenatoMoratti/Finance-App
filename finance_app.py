"""
🏦 APLICATIVO FINANCE - CONEXÃO COM MEU PLUGGY
==============================================

Este aplicativo conecta com sua conta do Meu Pluggy via OAuth
e busca suas contas bancárias e transações financeiras.

Requisitos:
- Conta ativa no Meu Pluggy (https://meu.pluggy.ai)
- Credenciais da API Pluggy configuradas no .env
"""

import requests
import json
import time
import webbrowser
from datetime import datetime
from time import perf_counter
from config import Config
from oauth_manager import OAuthManager


class FinanceApp:
    def __init__(self):
        self.base_url = Config.PLUGGY_BASE_URL
        self.client_id = Config.CLIENT_ID
        self.client_secret = Config.CLIENT_SECRET
        self.api_key = None
        self.current_item_id = None
        self.oauth_manager = OAuthManager()
        
    def print_header(self, title):
        """Imprime cabeçalho formatado"""
        print(f"\n{'='*60}")
        print(f"📱 {title}")
        print(f"{'='*60}")
        
    def print_step(self, step_num, title):
        """Imprime título de passo"""
        print(f"\n🔹 **PASSO {step_num}: {title}**")
        
    def force_update_account_data(self, item_id):
        """Força atualização dos dados da conta no Meu Pluggy antes de sincronizar"""
        try:
            print(f"🔄 Tentando atualizar dados da conta {item_id}...")
            
            # Primeiro verifica se é MeuPluggy (sandbox)
            item_response = requests.get(
                f"{self.base_url}/items/{item_id}",
                headers={"X-API-KEY": self.api_key}
            )
            
            if item_response.status_code == 200:
                item_data = item_response.json()
                connector_name = item_data.get('connector', {}).get('name', '')
                is_sandbox = item_data.get('connector', {}).get('isSandbox', False)
                last_updated = item_data.get('lastUpdatedAt', '')
                status = item_data.get('status', '')
                
                print(f"📊 Connector: {connector_name}")
                print(f"📊 Status: {status}")
                print(f"📊 Última atualização: {last_updated}")
                
                if connector_name == 'MeuPluggy':
                    print("💡 MeuPluggy detectado - verificando dados disponíveis...")
                    
                    # Para MeuPluggy, vamos verificar se há dados mais recentes
                    # e fazer uma sincronização direta dos dados disponíveis
                    self._check_data_freshness(item_id)
                    return True
            
            # Para conectores reais (bancos), tenta diferentes endpoints para refresh
            print("🏦 Banco real detectado - tentando refresh...")
            endpoints_to_try = [
                f"/items/{item_id}/refresh",
                f"/items/{item_id}/sync", 
                f"/items/{item_id}/update",
                f"/items/{item_id}/execute"
            ]
            
            for endpoint in endpoints_to_try:
                print(f"🔄 Tentando: POST {endpoint}")
                
                response = requests.post(
                    f"{self.base_url}{endpoint}",
                    headers={
                        "X-API-KEY": self.api_key,
                        "Content-Type": "application/json"
                    }
                )
                
                print(f"📊 Status: {response.status_code}")
                
                if response.status_code == 200:
                    print("✅ Solicitação de atualização enviada com sucesso!")
                    return self._monitor_update_status(item_id)
                elif response.status_code == 202:
                    print("✅ Atualização aceita e em processamento!")
                    return self._monitor_update_status(item_id)
                elif response.status_code == 403:
                    print(f"❌ Acesso negado para {endpoint}")
                    continue
                elif response.status_code == 400:
                    print(f"❌ Requisição inválida para {endpoint}: {response.text}")
                    continue
                else:
                    print(f"⚠️ Resposta inesperada {response.status_code}: {response.text}")
                    continue
            
            print("⚠️ Nenhum endpoint de refresh funcionou")
            print("💡 Continuando com dados disponíveis...")
            return True
                
        except Exception as e:
            print(f"❌ Erro ao tentar atualização: {e}")
            print("📝 Continuando com dados em cache...")
            return True  # Continua mesmo com erro na atualização

    def _check_data_freshness(self, item_id):
        """Verifica a atualidade dos dados para MeuPluggy"""
        try:
            print("🔍 Verificando dados disponíveis...")
            
            # Verifica contas disponíveis
            accounts_response = requests.get(
                f"{self.base_url}/accounts?itemId={item_id}",
                headers={"X-API-KEY": self.api_key}
            )
            
            if accounts_response.status_code == 200:
                accounts = accounts_response.json().get('results', [])
                print(f"💰 {len(accounts)} contas encontradas")
                
                # Verifica transações disponíveis
                transactions_response = requests.get(
                    f"{self.base_url}/transactions?itemId={item_id}",
                    headers={"X-API-KEY": self.api_key}
                )
                
                if transactions_response.status_code == 200:
                    transactions = transactions_response.json().get('results', [])
                    print(f"💳 {len(transactions)} transações encontradas")
                    
                    if transactions:
                        # Encontra a transação mais recente
                        latest_transaction = max(transactions, key=lambda x: x.get('date', ''))
                        latest_date = latest_transaction.get('date', '')
                        print(f"📅 Transação mais recente: {latest_date}")
                    
                print("✅ Dados do MeuPluggy verificados e disponíveis")
            else:
                print("⚠️ Erro ao verificar dados do MeuPluggy")
                
        except Exception as e:
            print(f"❌ Erro na verificação: {e}")

    def _monitor_update_status(self, item_id):
        """Monitora o status da atualização"""
        try:
            print("⏳ Monitorando progresso da atualização...")
            
            for attempt in range(30):  # Máximo 30 tentativas (2 minutos)
                time.sleep(4)
                
                status_response = requests.get(
                    f"{self.base_url}/items/{item_id}",
                    headers={"X-API-KEY": self.api_key}
                )
                
                if status_response.status_code == 200:
                    item_data = status_response.json()
                    status = item_data.get('status')
                    execution_status = item_data.get('executionStatus')
                    
                    print(f"📊 Status: {status} | Execução: {execution_status}")
                    
                    if status in ['CONNECTED', 'UPDATED'] and execution_status == 'SUCCESS':
                        print("✅ Dados atualizados com sucesso!")
                        return True
                    elif status in ['LOGIN_ERROR', 'OUTDATED'] or execution_status == 'ERROR':
                        print("❌ Erro na atualização dos dados")
                        return False
                    elif status in ['UPDATING', 'LOGIN_IN_PROGRESS'] or execution_status in ['RUNNING', 'PENDING']:
                        print(f"🔄 Ainda atualizando... (tentativa {attempt + 1}/30)")
                        continue
                
                time.sleep(1)
            
            print("⚠️ Timeout na atualização, mas continuando...")
            return True
            
        except Exception as e:
            print(f"❌ Erro no monitoramento: {e}")
            return True

    def authenticate(self):
        """Autentica na API Pluggy"""
        self.print_step(1, "AUTENTICAÇÃO")
        
        print("🔐 Conectando com a API Pluggy...")
        
        try:
            response = requests.post(
                f"{self.base_url}/auth",
                headers={"Content-Type": "application/json"},
                json={"clientId": self.client_id, "clientSecret": self.client_secret}
            )
            response.raise_for_status()
            
            self.api_key = response.json().get('apiKey')
            
            if not self.api_key:
                print("❌ Erro: API Key não recebida")
                return False
                
            print("✅ Autenticação bem-sucedida!")
            return True
            
        except Exception as e:
            print(f"❌ Erro na autenticação: {e}")
            return False
    
    def create_oauth_connection(self):
        """Cria uma conexão OAuth com o Meu Pluggy"""
        self.print_step(2, "CRIAÇÃO DA CONEXÃO OAUTH")
        
        print("🔗 Criando conexão OAuth com Meu Pluggy...")
        
        try:
            # Cria item OAuth
            response = requests.post(
                f"{self.base_url}/items",
                headers={"Content-Type": "application/json", "X-API-KEY": self.api_key},
                json={"connectorId": 200, "parameters": {}}  # 200 = MeuPluggy
            )
            response.raise_for_status()
            
            item_data = response.json()
            self.current_item_id = item_data.get('id')
            
            print(f"✅ Item OAuth criado: {self.current_item_id}")
            
            # Salva dados OAuth temporários
            self.oauth_manager.save_oauth_data(
                item_id=self.current_item_id,
                status="pending"
            )
            
            # Aguarda URL OAuth
            return self.wait_for_oauth_url()
            
        except Exception as e:
            print(f"❌ Erro ao criar conexão: {e}")
            return False
    
    def wait_for_oauth_url(self, max_attempts=10):
        """Aguarda e obtém a URL OAuth"""
        print("⏳ Aguardando URL de autorização...")
        
        for attempt in range(max_attempts):
            try:
                response = requests.get(
                    f"{self.base_url}/items/{self.current_item_id}",
                    headers={"X-API-KEY": self.api_key}
                )
                response.raise_for_status()
                
                item_data = response.json()
                parameter = item_data.get('parameter')
                
                if parameter and isinstance(parameter, dict) and 'data' in parameter:
                    oauth_url = parameter['data']
                    expires_at = parameter.get('expiresAt')
                    
                    print(f"✅ URL OAuth obtida!")
                    print(f"⏰ Expira em: {expires_at}")
                    print(f"\n🔗 **URL DE AUTORIZAÇÃO:**")
                    print(f"{oauth_url}")
                    
                    # Pergunta se quer abrir automaticamente
                    choice = input("\n🌐 Deseja abrir a URL automaticamente no navegador? (s/n): ")
                    if choice.lower() in ['s', 'sim', 'y', 'yes']:
                        webbrowser.open(oauth_url)
                        print("🚀 Navegador aberto!")
                    
                    print(f"\n📋 **INSTRUÇÕES:**")
                    print("1. Acesse a URL no navegador")
                    print("2. Faça login na sua conta do Meu Pluggy")
                    print("3. Autorize o acesso aos seus dados bancários")
                    print("4. Aguarde o redirecionamento")
                    
                    # Aguarda autorização
                    return self.wait_for_authorization()
                
                print(f"   Tentativa {attempt + 1}/{max_attempts} - Aguardando...")
                time.sleep(2)
                
            except Exception as e:
                print(f"❌ Erro ao verificar status: {e}")
                return False
        
        print("❌ Timeout: URL OAuth não obtida")
        return False
    
    def wait_for_authorization(self, max_attempts=30):
        """Aguarda a autorização OAuth do usuário"""
        self.print_step(3, "AGUARDANDO AUTORIZAÇÃO")
        
        print("⏳ Aguardando você completar a autorização...")
        print("📱 Complete o processo no navegador e pressione qualquer tecla...")
        
        input("⏸️  Pressione ENTER após completar a autorização: ")
        
        # Verifica se a autorização foi concluída
        for attempt in range(max_attempts):
            try:
                response = requests.get(
                    f"{self.base_url}/items/{self.current_item_id}",
                    headers={"X-API-KEY": self.api_key}
                )
                response.raise_for_status()
                
                item_data = response.json()
                status = item_data.get('status')
                
                print(f"   Verificação {attempt + 1}: Status = {status}")
                
                if status == 'UPDATED':
                    print("✅ Autorização concluída com sucesso!")
                    # Salva conexão OAuth como ativa
                    self.oauth_manager.save_oauth_data(
                        item_id=self.current_item_id,
                        status="active"
                    )
                    return True
                elif status == 'LOGIN_ERROR':
                    print("❌ Erro na autorização. Tente novamente.")
                    return False
                elif status == 'OUTDATED':
                    print("⚠️ Autorização expirada.")
                    return False
                
                time.sleep(3)
                
            except Exception as e:
                print(f"❌ Erro ao verificar autorização: {e}")
                return False
        
        print("⏰ Timeout: Autorização não confirmada")
        return False
    
    def fetch_accounts(self):
        """Busca contas bancárias"""
        self.print_step(4, "BUSCANDO CONTAS BANCÁRIAS")
        
        try:
            response = requests.get(
                f"{self.base_url}/accounts",
                headers={"X-API-KEY": self.api_key},
                params={"itemId": self.current_item_id}
            )
            response.raise_for_status()
            
            accounts_data = response.json()
            accounts = accounts_data.get('results', [])
            
            if not accounts:
                print("⚠️ Nenhuma conta encontrada")
                return []
            
            print(f"✅ Encontradas {len(accounts)} contas:")
            
            total_balance = 0
            for i, account in enumerate(accounts, 1):
                name = account.get('name', 'Conta sem nome')
                balance = account.get('balance', 0)
                acc_type = account.get('type', 'N/A')
                
                print(f"   {i}. 🏦 {name}")
                print(f"      💰 Saldo: R$ {balance:.2f}")
                print(f"      🏷️ Tipo: {acc_type}")
                
                total_balance += balance
            
            print(f"\n💎 **SALDO TOTAL: R$ {total_balance:.2f}**")
            
            return accounts
            
        except Exception as e:
            print(f"❌ Erro ao buscar contas: {e}")
            return []
    
    def fetch_transactions(self, accounts):
        """Busca transações de todas as contas - COM PAGINAÇÃO COMPLETA"""
        self.print_step(5, "BUSCANDO TRANSAÇÕES")
        
        all_transactions = []
        total_found = 0
        
        for account in accounts:
            account_id = account.get('id')
            account_name = account.get('name', 'Conta')
            
            print(f"\n💳 Buscando TODAS transações de: {account_name}")
            
            try:
                account_transactions = []
                page = 1
                page_size = 500  # Máximo por página
                
                while True:
                    response = requests.get(
                        f"{self.base_url}/transactions",
                        headers={"X-API-KEY": self.api_key},
                        params={
                            "itemId": self.current_item_id, 
                            "accountId": account_id, 
                            "pageSize": page_size,
                            "page": page
                        }
                    )
                    response.raise_for_status()
                    
                    transactions_data = response.json()
                    transactions = transactions_data.get('results', [])
                    total_results = transactions_data.get('totalResults', 0)
                    
                    if not transactions:
                        break
                    
                    # Adiciona informações da conta
                    for transaction in transactions:
                        transaction['account_name'] = account_name
                        transaction['account_id'] = account_id
                    
                    account_transactions.extend(transactions)
                    
                    print(f"   📄 Página {page}: {len(transactions)} transações")
                    
                    # Se pegamos menos que o page_size, chegamos ao fim
                    if len(transactions) < page_size:
                        break
                    
                    page += 1
                
                all_transactions.extend(account_transactions)
                total_found += len(account_transactions)
                print(f"   ✅ {len(account_transactions)} transações encontradas em {account_name}")
                
            except Exception as e:
                print(f"   ❌ Erro ao buscar transações de {account_name}: {e}")
        
        print(f"\n🎯 **TOTAL: {total_found} transações encontradas em todas as contas**")
        return all_transactions
    
    def display_transaction_summary(self, transactions):
        """Exibe resumo das transações"""
        self.print_step(6, "RESUMO DAS TRANSAÇÕES")
        
        if not transactions:
            print("❌ Nenhuma transação para exibir")
            return
        
        print(f"📊 **TOTAL DE TRANSAÇÕES: {len(transactions)}**\n")
        
        # Últimas 10 transações
        print("🕐 **ÚLTIMAS 10 TRANSAÇÕES:**")
        for i, trans in enumerate(transactions[:10], 1):
            amount = trans.get('amount', 0)
            desc = trans.get('description', 'Sem descrição')
            date = trans.get('date', 'N/A')[:10]  # Só a data
            account = trans.get('account_name', 'N/A')
            
            emoji = "💚" if amount > 0 else "🔴"
            sign = "+" if amount > 0 else "-"
            
            print(f"   {i:2d}. {emoji} {sign} R$ {abs(amount):.2f}")
            print(f"       📅 {date} | 🏦 {account}")
            print(f"       📝 {desc}")
            print()
        
        # Estatísticas
        income = sum(t.get('amount', 0) for t in transactions if t.get('amount', 0) > 0)
        expense = sum(t.get('amount', 0) for t in transactions if t.get('amount', 0) < 0)
        
        print("📈 **ESTATÍSTICAS:**")
        print(f"   💚 Total de entradas: R$ {income:.2f}")
        print(f"   🔴 Total de saídas: R$ {abs(expense):.2f}")
        print(f"   📊 Saldo líquido: R$ {income + expense:.2f}")
    
    def save_to_database(self, accounts, transactions):
        """Salva dados no banco de dados e retorna estatísticas detalhadas"""
        try:
            from database import Database
            db = Database()
            
            # Chama a sincronização incremental que retorna estatísticas
            result = db.save_sync_data_incremental_with_stats(
                item_id=self.current_item_id,
                accounts=accounts,
                transactions=transactions
            )
            
            if result and result.get('success'):
                stats = result.get('stats', {})
                print(f"\n💾 **DADOS SALVOS NO BANCO DE DADOS**")
                print(f"📊 Estatísticas da sincronização:")
                print(f"   💳 Contas: {stats.get('accounts_inserted', 0)} inseridas, {stats.get('accounts_updated', 0)} atualizadas, {stats.get('accounts_unchanged', 0)} inalteradas")
                print(f"   💰 Transações: {stats.get('transactions_inserted', 0)} inseridas, {stats.get('transactions_updated', 0)} atualizadas, {stats.get('transactions_unchanged', 0)} inalteradas")
                return result
            else:
                print(f"\n❌ **ERRO AO SALVAR NO BANCO**")
                return {'success': False, 'message': 'Erro ao salvar dados'}
                
        except Exception as e:
            print(f"❌ Erro ao salvar no banco: {e}")
            return {'success': False, 'message': f'Erro: {e}'}
    
    def sync_existing_connection(self):
        """Sincroniza dados usando conexões OAuth existentes com atualização forçada"""
        try:
            t0_total = perf_counter()
            # Verifica se tem conexões válidas
            if not self.oauth_manager.has_valid_connection():
                return False, "Nenhuma conexão OAuth válida encontrada"
            
            # Autentica
            if not self.authenticate():
                return False, "Erro na autenticação"
            
            # Busca dados de todas as conexões ativas
            all_accounts = []
            all_transactions = []
            active_connections = self.oauth_manager.get_active_connections()
            
            print(f"🚀 Iniciando sincronização com atualização forçada para {len(active_connections)} conexão(ões)...")
            
            for item_id, connection_info in active_connections.items():
                bank_name = connection_info.get('bank_name', f'Banco_{item_id[:8]}')
                print(f"🔄 Sincronizando {bank_name}...")
                t_conn_start = perf_counter()
                # FORÇA ATUALIZAÇÃO DOS DADOS NO MEU PLUGGY PRIMEIRO
                print(f"🚀 Atualizando dados de {bank_name}...")
                t_force = perf_counter()
                self.force_update_account_data(item_id)
                t_force_end = perf_counter()
                
                # Usa item_id específico
                self.current_item_id = item_id
                
                # Busca contas desta conexão (agora atualizadas)
                t_accounts_start = perf_counter()
                accounts = self.fetch_accounts_silent()
                t_accounts_end = perf_counter()
                if accounts:
                    # Adiciona informação da conexão às contas
                    for account in accounts:
                        account['connection_name'] = bank_name
                        account['item_id'] = item_id
                    all_accounts.extend(accounts)
                    
                    # Busca transações desta conexão
                    t_tx_start = perf_counter()
                    transactions = self.fetch_transactions_silent(accounts)
                    t_tx_end = perf_counter()
                    if transactions:
                        # Adiciona informação da conexão às transações
                        for transaction in transactions:
                            transaction['connection_name'] = bank_name
                            transaction['item_id'] = item_id
                        all_transactions.extend(transactions)
                t_conn_end = perf_counter()
                print(
                    f"⏱️ Tempo {bank_name}: force={t_force_end - t_force:.2f}s contas={t_accounts_end - t_accounts_start:.2f}s transações={(t_tx_end - t_tx_start) if 't_tx_end' in locals() else 0:.2f}s total={t_conn_end - t_conn_start:.2f}s"
                )
            
            if not all_accounts:
                return False, "Nenhuma conta encontrada nas conexões"
            
            # Salva no banco
            t_db_start = perf_counter()
            result = self.save_to_database(all_accounts, all_transactions)
            t_db_end = perf_counter()
            
            if result and result.get('success'):
                stats = result.get('stats', {})
                connections_count = len(active_connections)
                
                # Monta mensagem detalhada com estatísticas
                accounts_msg = f"{stats.get('accounts_inserted', 0)} novas, {stats.get('accounts_updated', 0)} atualizadas, {stats.get('accounts_unchanged', 0)} inalteradas"
                transactions_msg = f"{stats.get('transactions_inserted', 0)} novas, {stats.get('transactions_updated', 0)} atualizadas, {stats.get('transactions_unchanged', 0)} inalteradas"
                
                message = f"Sincronização incremental concluída: {connections_count} conexões processadas\n"
                message += f"💳 Contas: {accounts_msg}\n"
                message += f"💰 Transações: {transactions_msg}"
                
                # Adiciona informação de conflitos se houver
                conflicts_count = stats.get('conflicts_detected', 0)
                if conflicts_count > 0:
                    message += f"\n⚠️ Conflitos: {conflicts_count} transações com conflitos detectados"
                
                total_time = perf_counter() - t0_total
                message += f"\n⏱️ Tempo total: {total_time:.2f}s (persistência {t_db_end - t_db_start:.2f}s)"
                return True, message
            else:
                error_msg = result.get('message', 'Erro ao salvar no banco de dados') if result else 'Erro ao salvar no banco de dados'
                return False, error_msg
                
        except Exception as e:
            return False, f"Erro na sincronização: {e}"
    
    def fetch_accounts_silent(self):
        """Busca contas sem output no console"""
        try:
            response = requests.get(
                f"{self.base_url}/accounts",
                headers={"X-API-KEY": self.api_key},
                params={"itemId": self.current_item_id}
            )
            response.raise_for_status()
            
            accounts_data = response.json()
            return accounts_data.get('results', [])
            
        except Exception:
            return []
    
    def fetch_transactions_silent(self, accounts):
        """Busca transações sem output no console - TODAS as transações com paginação.

        Aplica filtro opcional por data inicial (data_since) definido por conexão.
        """
        t_accounts_loop_start = perf_counter()
        all_transactions: list[dict] = []
        connections = self.oauth_manager.load_all_connections()

        for account in accounts:
            try:
                print(f"📊 Buscando TODAS transações de {account.get('name', 'Conta')}...")
                account_transactions: list[dict] = []
                page = 1
                page_size = 500
                while True:
                    t_page_start = perf_counter()
                    response = requests.get(
                        f"{self.base_url}/transactions",
                        headers={"X-API-KEY": self.api_key},
                        params={
                            "itemId": self.current_item_id,
                            "accountId": account.get('id'),
                            "pageSize": page_size,
                            "page": page
                        }
                    )
                    response.raise_for_status()
                    data = response.json()
                    transactions = data.get('results', [])
                    total_results = data.get('totalResults', 0)
                    if not transactions:
                        break

                    filtered = []
                    for tr in transactions:
                        tr['account_name'] = account.get('name', 'Conta')
                        tr['account_id'] = account.get('id')
                        item_id_local = self.current_item_id
                        data_since = None
                        if item_id_local and item_id_local in connections:
                            data_since = connections[item_id_local].get('data_since')
                        if data_since and tr.get('date') and tr['date'][:10] < data_since:
                            continue
                        filtered.append(tr)
                    account_transactions.extend(filtered)

                    t_page_end = perf_counter()
                    print(
                        f"   📄 Página {page}: {len(filtered)}/{len(transactions)} válidas (Total na conta: {len(account_transactions)}/{total_results}) em {t_page_end - t_page_start:.2f}s"
                    )
                    if len(transactions) < page_size:
                        break
                    page += 1

                all_transactions.extend(account_transactions)
                print(
                    f"   ✅ {len(account_transactions)} transações carregadas (após filtro) para {account.get('name', 'Conta')}"
                )
            except Exception as e:
                print(
                    f"   ❌ Erro ao buscar transações de {account.get('name', 'Conta')}: {e}"
                )
                continue

        print(
            f"🎯 TOTAL FINAL: {len(all_transactions)} transações de todas as contas (após filtros) em {perf_counter() - t_accounts_loop_start:.2f}s"
        )
        return all_transactions
    
    def get_oauth_status(self):
        """Retorna status da conexão OAuth"""
        if self.oauth_manager.has_valid_connection():
            data = self.oauth_manager.load_oauth_data()
            return {
                'connected': True,
                'item_id': data.get('item_id'),
                'status': data.get('status'),
                'created_at': data.get('created_at'),
                'last_updated': data.get('last_updated')
            }
        else:
            return {'connected': False}
    
    def reset_oauth_connection(self):
        """Remove conexão OAuth para reconectar"""
        return self.oauth_manager.clear_oauth_data()
    
    def run(self, skip_oauth=False):
        """Executa o aplicativo principal"""
        self.print_header("FINANCE APP - MEU PLUGGY")
        
        print("🏦 Bem-vindo ao Finance App!")
        print("📱 Este app conecta com sua conta do Meu Pluggy via OAuth")
        print("🔐 e busca suas informações financeiras de forma segura.")
        
        # Verifica credenciais
        if self.client_id == "your_client_id_here":
            print("\n❌ **ERRO: Configure suas credenciais!**")
            print("1. Edite o arquivo .env")
            print("2. Configure PLUGGY_CLIENT_ID e PLUGGY_CLIENT_SECRET")
            return False
        
        try:
            # Autentica na API
            if not self.authenticate():
                return False
            
            # Verifica se já existe conexão OAuth válida
            if not skip_oauth and self.oauth_manager.has_valid_connection():
                self.current_item_id = self.oauth_manager.get_item_id()
                print(f"✅ Usando conexão OAuth existente: {self.current_item_id}")
            elif not skip_oauth:
                # Precisa fazer OAuth
                if not self.create_oauth_connection():
                    return False
            
            # Se temos item_id, busca dados
            if self.current_item_id:
                accounts = self.fetch_accounts()
                if not accounts:
                    print("⚠️ Sem contas para processar")
                    return False
                
                transactions = self.fetch_transactions(accounts)
                
                self.display_transaction_summary(transactions)
                
                self.save_to_database(accounts, transactions)
                
                # Sucesso!
                print(f"\n🎉 **PROCESSO CONCLUÍDO COM SUCESSO!**")
                print("✅ Conexão OAuth estabelecida")
                print("✅ Contas bancárias obtidas")
                print("✅ Transações sincronizadas")
                print("✅ Dados salvos no banco de dados")
                
                return True
            else:
                print("❌ Nenhuma conexão OAuth disponível")
                return False
            
        except KeyboardInterrupt:
            print("\n⏹️ Processo interrompido pelo usuário")
            return False
        except Exception as e:
            print(f"\n❌ Erro inesperado: {e}")
            return False
    
    def create_oauth_connection_with_name(self, bank_name: str = None):
        """Cria nova conexão OAuth com nome personalizado"""
        try:
            if not self.authenticate():
                print("❌ Erro na autenticação")
                return False
            
            print(f"🔄 Criando conexão OAuth para: {bank_name or 'Nova conta'}...")
            
            # Primeiro, vamos listar os conectores para encontrar o Meu Pluggy
            print("🔍 Buscando conector do Meu Pluggy...")
            connectors_response = requests.get(
                f"{self.base_url}/connectors",
                headers={"X-API-KEY": self.api_key}
            )
            
            if connectors_response.status_code == 200:
                connectors = connectors_response.json().get('results', [])
                meu_pluggy_connector = None
                
                for connector in connectors:
                    if 'meu' in connector.get('name', '').lower() and 'pluggy' in connector.get('name', '').lower():
                        meu_pluggy_connector = connector
                        break
                
                if meu_pluggy_connector:
                    connector_id = meu_pluggy_connector['id']
                    print(f"✅ Conector Meu Pluggy encontrado! ID: {connector_id}")
                    print(f"   Nome: {meu_pluggy_connector.get('name')}")
                    print(f"   Tipo: {meu_pluggy_connector.get('type')}")
                else:
                    print("❌ Conector Meu Pluggy não encontrado!")
                    # Vamos usar um ID genérico para teste
                    connector_id = 201
            else:
                print("⚠️  Não foi possível listar conectores, usando ID padrão")
                connector_id = 201
            
            # Cria item no Pluggy para Meu Pluggy OAuth
            # Torna clientUserId único para evitar OUTDATED prematuro (colisão de sessão)
            client_user_id = f"financeapp_{int(time.time())}"[:40]
            payload = {
                "connectorId": connector_id,
                "parameters": {},  # OAuth não precisa de credenciais aqui
                "clientUserId": client_user_id
                # "webhookUrl": "https://seu-endpoint-webhook"  # opcional
            }
            
            print(f"📤 Enviando payload: {payload}")
            
            response = requests.post(
                f"{self.base_url}/items",
                headers={"X-API-KEY": self.api_key, "Content-Type": "application/json"},
                json=payload,
                timeout=30
            )
            
            print(f"📥 Status da resposta: {response.status_code}")
            print(f"📥 Resposta: {response.text}")
            
            response.raise_for_status()
            
            item_data = response.json()
            item_id = item_data.get('id')
            
            print(f"✅ Item OAuth criado: {item_id}")
            
            # Salva dados OAuth com nome personalizado
            self.oauth_manager.save_oauth_data(
                item_id=item_id,
                bank_name=bank_name or f"Conta_{item_id[:8]}",
                status="pending"
            )
            
            self.current_item_id = item_id
            
            # Obtém URL OAuth
            oauth_url = self.get_oauth_url_for_item(item_id, retry_if_outdated=True)
            if oauth_url:
                # Atualiza registro com URL
                try:
                    self.oauth_manager.save_oauth_data(
                        item_id=item_id,
                        bank_name=bank_name or f"Conta_{item_id[:8]}",
                        status="pending",
                        oauth_url=oauth_url
                    )
                except Exception as e_save:
                    print(f"⚠️ Não foi possível atualizar oauth_url salvo: {e_save}")
                return item_id, oauth_url
            else:
                print("❌ Falha ao obter URL OAuth após tentativas")
                return False
            
        except Exception as e:
            print(f"❌ Erro ao criar conexão: {e}")
            return False
    
    def get_oauth_url_for_item(self, item_id: str, retry_if_outdated: bool = False):
        """Obtém URL OAuth para um item específico.

        Melhorias:
        - Aumenta número de tentativas
        - Faz log detalhado se parâmetro vier nulo
        - Opcionalmente recria item ao receber OUTDATED antes da URL
        """
        print("⏳ Aguardando URL de autorização...")
        last_status = None
        for attempt in range(30):  # até ~60s
            try:
                response = requests.get(
                    f"{self.base_url}/items/{item_id}",
                    headers={"X-API-KEY": self.api_key},
                    timeout=15
                )
                if response.status_code != 200:
                    print(f"⚠️ Tentativa {attempt+1}: HTTP {response.status_code}")
                    time.sleep(2)
                    continue
                item_data = response.json()
                status = item_data.get('status')
                execution = item_data.get('executionStatus')
                parameter = item_data.get('parameter')
                if status != last_status:
                    print(f"   Status mudou: {status} (exec={execution})")
                    last_status = status
                else:
                    print(f"   Tentativa {attempt+1}: {status} (param={'ok' if parameter else 'vazio'})")

                # URL disponível
                if status == 'WAITING_USER_INPUT' and parameter:
                    oauth_url = parameter.get('data') or parameter.get('url')
                    if oauth_url:
                        print(f"✅ URL OAuth obtida: {oauth_url[:60]}...")
                        return oauth_url

                if status == 'UPDATED':
                    print("✅ Item já autorizado anteriormente")
                    return "already_authorized"

                if status in ['OUTDATED', 'LOGIN_ERROR']:
                    print(f"⚠️ Recebido status {status} antes de obter URL")
                    if retry_if_outdated and status == 'OUTDATED':
                        print("🔁 Tentando recriar item por OUTDATED precoce...")
                        # Recriar rapidamente uma única vez
                        if attempt < 5:  # só se aconteceu cedo
                            try:
                                recreate = requests.post(
                                    f"{self.base_url}/items",
                                    headers={"X-API-KEY": self.api_key, "Content-Type": "application/json"},
                                    json={"connectorId": 200, "parameters": {}, "clientUserId": f"retry_{int(time.time())}"},
                                    timeout=30
                                )
                                if recreate.status_code == 201 or recreate.status_code == 200:
                                    new_id = recreate.json().get('id')
                                    if new_id and new_id != item_id:
                                        print(f"✅ Novo item criado para retry: {new_id}")
                                        item_id = new_id
                                        continue
                            except Exception as rec_e:
                                print(f"❌ Falha ao recriar item: {rec_e}")
                    return None

                time.sleep(2)
            except Exception as e:
                print(f"❌ Erro na tentativa {attempt+1}: {e}")
                time.sleep(2)
        print("❌ Timeout aguardando URL OAuth (sem sucesso)")
        return None
    
    def sync_single_connection(self, item_id: str):
        """Sincroniza uma conexão específica com atualização forçada"""
        try:
            if not self.authenticate():
                print("❌ Erro na autenticação")
                return False
            
            print(f"🔄 Sincronizando conexão {item_id}...")
            
            # FORÇA ATUALIZAÇÃO DOS DADOS NO MEU PLUGGY PRIMEIRO
            print("🚀 Atualizando dados no Meu Pluggy...")
            update_success = self.force_update_account_data(item_id)
            
            if not update_success:
                print("⚠️ Falha na atualização forçada, mas continuando...")
            
            # Verifica status da conexão após atualização
            response = requests.get(
                f"{self.base_url}/items/{item_id}",
                headers={"X-API-KEY": self.api_key}
            )
            
            if response.status_code != 200:
                print("❌ Erro ao verificar conexão")
                return False
            
            item_data = response.json()
            status = item_data.get('status')
            
            if status not in ['UPDATED', 'CONNECTED']:
                print(f"⚠️  Conexão não está ativa. Status: {status}")
                return False
            
            print("✅ Dados atualizados! Buscando contas e transações...")
            
            # Busca contas (agora com dados atualizados)
            accounts_response = requests.get(
                f"{self.base_url}/accounts",
                headers={"X-API-KEY": self.api_key},
                params={"itemId": item_id}
            )
            
            accounts = []
            if accounts_response.status_code == 200:
                accounts_data = accounts_response.json()
                accounts = accounts_data.get('results', [])
                
                # Adiciona informações da conexão
                connection_info = self.oauth_manager.get_connection_info(item_id)
                bank_name = connection_info.get('bank_name', f'Banco_{item_id[:8]}') if connection_info else f'Banco_{item_id[:8]}'
                
                for account in accounts:
                    account['connection_name'] = bank_name
                    account['item_id'] = item_id

            # Busca TODAS as transações com paginação completa
            print("🔄 Buscando TODAS as transações com paginação...")
            all_transactions = []
            page = 1
            page_size = 500
            
            while True:
                transactions_response = requests.get(
                    f"{self.base_url}/transactions",
                    headers={"X-API-KEY": self.api_key},
                    params={
                        "itemId": item_id, 
                        "pageSize": page_size,
                        "page": page
                    }
                )
                
                if transactions_response.status_code == 200:
                    transactions_data = transactions_response.json()
                    transactions = transactions_data.get('results', [])
                    total_results = transactions_data.get('totalResults', 0)
                    
                    if not transactions:
                        break
                    
                    # Adiciona informações da conexão
                    connection_info = self.oauth_manager.get_connection_info(item_id)
                    bank_name = connection_info.get('bank_name', f'Banco_{item_id[:8]}') if connection_info else f'Banco_{item_id[:8]}'
                    
                    filtered_page = []
                    connection_info_local = self.oauth_manager.get_connection_info(item_id)
                    data_since = connection_info_local.get('data_since') if connection_info_local else None
                    for transaction in transactions:
                        # aplica filtro antes de guardar
                        if data_since and transaction.get('date') and transaction['date'][:10] < data_since:
                            continue
                        transaction['connection_name'] = bank_name
                        transaction['item_id'] = item_id
                        filtered_page.append(transaction)

                    all_transactions.extend(filtered_page)
                    
                    print(f"   📄 Página {page}: {len(transactions)} transações (Total: {len(all_transactions)}/{total_results})")
                    
                    # Se pegamos menos que o page_size, chegamos ao fim
                    if len(transactions) < page_size:
                        break
                    
                    page += 1
                else:
                    print(f"❌ Erro na página {page}: {transactions_response.status_code}")
                    break

            # Salva usando sincronização incremental
            self.current_item_id = item_id
            result = self.save_to_database(accounts, all_transactions)
            
            if result and result.get('success'):
                # Atualiza status da conexão
                self.oauth_manager.update_status(item_id, 'active')
                
                stats = result.get('stats', {})
                return {
                    'accounts': stats.get('accounts_inserted', 0) + stats.get('accounts_updated', 0),
                    'transactions': stats.get('transactions_inserted', 0) + stats.get('transactions_updated', 0),
                    'status': 'active',
                    'stats': stats
                }
            else:
                return False
            
        except Exception as e:
            print(f"❌ Erro na sincronização: {e}")
            return False
    
    def save_accounts_to_db(self, accounts, item_id):
        """Salva contas no banco de dados associadas à conexão"""
        try:
            import sqlite3
            
            conn = sqlite3.connect('data/finance_app.db')
            cursor = conn.cursor()
            
            # Busca informações da conexão para associar
            connection_info = self.oauth_manager.get_connection_info(item_id)
            connection_name = connection_info.get('bank_name', 'Desconhecido') if connection_info else 'Desconhecido'
            
            # Cria tabela de conexões se não existir
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS connections (
                    item_id TEXT PRIMARY KEY,
                    bank_name TEXT NOT NULL,
                    status TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')
            
            # Insere ou atualiza informações da conexão
            cursor.execute('''
                INSERT OR REPLACE INTO connections 
                (item_id, bank_name, status, created_at, updated_at)
                VALUES (?, ?, ?, datetime('now'), datetime('now'))
            ''', (
                item_id,
                connection_name,
                'active'
            ))
            
            # Cria tabela de contas se não existir
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS accounts (
                    id TEXT PRIMARY KEY,
                    item_id TEXT NOT NULL,
                    connection_name TEXT,
                    name TEXT,
                    type TEXT,
                    subtype TEXT,
                    balance REAL,
                    currency TEXT,
                    bank_name TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    FOREIGN KEY (item_id) REFERENCES connections (item_id)
                )
            ''')
            
            for account in accounts:
                cursor.execute('''
                    INSERT OR REPLACE INTO accounts 
                    (id, item_id, connection_name, name, type, subtype, balance, currency, bank_name, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    account.get('id'),
                    item_id,
                    connection_name,
                    account.get('name'),
                    account.get('type'),
                    account.get('subtype'),
                    account.get('balance', 0),
                    account.get('currencyCode', 'BRL'),
                    account.get('bankData', {}).get('name', connection_name),
                    account.get('createdAt'),
                    account.get('updatedAt')
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"❌ Erro ao salvar contas: {e}")
    
    def save_transactions_to_db(self, transactions, item_id):
        """Salva transações no banco de dados associadas à conexão - COM PAGINAÇÃO MELHORADA"""
        try:
            import sqlite3
            
            conn = sqlite3.connect('data/finance_app.db')
            cursor = conn.cursor()
            
            # Busca informações da conexão
            connection_info = self.oauth_manager.get_connection_info(item_id)
            connection_name = connection_info.get('bank_name', 'Desconhecido') if connection_info else 'Desconhecido'
            
            print(f"💾 Salvando {len(transactions)} transações de {connection_name}...")
            
            # Cria tabela de transações se não existir
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id TEXT PRIMARY KEY,
                    item_id TEXT NOT NULL,
                    connection_name TEXT,
                    account_id TEXT,
                    account_name TEXT,
                    description TEXT,
                    amount REAL,
                    currency TEXT,
                    date TEXT,
                    type TEXT,
                    category TEXT,
                    merchant_name TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    FOREIGN KEY (item_id) REFERENCES connections (item_id),
                    FOREIGN KEY (account_id) REFERENCES accounts (id)
                )
            ''')
            
            saved_count = 0
            for transaction in transactions:
                # Busca nome da conta associada
                account_id = transaction.get('accountId')
                account_name = 'Desconhecida'
                
                if account_id:
                    cursor.execute('SELECT name FROM accounts WHERE id = ?', (account_id,))
                    account_result = cursor.fetchone()
                    if account_result:
                        account_name = account_result[0]
                
                cursor.execute('''
                    INSERT OR REPLACE INTO transactions 
                    (id, item_id, connection_name, account_id, account_name, description, amount, currency, date, type, category, merchant_name, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    transaction.get('id'),
                    item_id,
                    connection_name,
                    account_id,
                    account_name,
                    transaction.get('description'),
                    transaction.get('amount', 0),
                    transaction.get('currencyCode', 'BRL'),
                    transaction.get('date'),
                    transaction.get('type'),
                    transaction.get('category'),
                    transaction.get('merchant', {}).get('name'),
                    transaction.get('createdAt'),
                    transaction.get('updatedAt')
                ))
                saved_count += 1
            
            conn.commit()
            conn.close()
            
            print(f"✅ {saved_count} transações salvas no banco de dados")
            
        except Exception as e:
            print(f"❌ Erro ao salvar transações: {e}")


def main():
    """Função principal"""
    app = FinanceApp()
    success = app.run()
    
    if success:
        print(f"\n💡 **PRÓXIMOS PASSOS:**")
        print("1. Execute novamente para atualizar dados")
        print("2. Verifique os arquivos salvos na pasta 'data/'")
        print("3. Mantenha sua conta do Meu Pluggy ativa")
    else:
        print(f"\n🔧 **SOLUÇÃO DE PROBLEMAS:**")
        print("1. Verifique sua conexão com internet")
        print("2. Confirme suas credenciais no .env")
        print("3. Certifique-se de ter conta ativa no Meu Pluggy")


if __name__ == "__main__":
    main()
