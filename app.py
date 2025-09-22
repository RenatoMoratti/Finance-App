"""
🌐 WEB APP - INTERFACE WEB PARA FINANCE APP
============================    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro na sincronização: {e}'})

@app.route('/reset_oauth', methods=['POST'])====

Interface web com Flask para:
- Sincronização de dados
- Visualização de contas
- Lista de transações com filtros
- Dashboard com estatísticas
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import json
import os
import time
import requests
import webbrowser
import threading
from datetime import datetime, timedelta
from database import Database
from finance_app import FinanceApp
from oauth_manager import OAuthManager
from config import Config
from settings_manager import settings_manager
from environment_manager import environment_manager
from backup_manager import perform_backup, start_periodic_backups

app = Flask(__name__)
app.secret_key = Config.FLASK_SECRET_KEY

# Context processor para disponibilizar contagem global de mapeamentos pendentes
@app.context_processor
def inject_pending_mappings():
    try:
        return {'pending_mappings_global': db.count_unmapped_categories()}
    except Exception:
        return {'pending_mappings_global': 0}

# Context processor para disponibilizar informações do ambiente
@app.context_processor
def inject_environment_info():
    try:
        return {'environment_info': environment_manager.get_environment_info()}
    except Exception:
        return {'environment_info': {'environment': 'development', 'environment_display': 'DEV'}}

# Função para formatação brasileira de valores
def format_currency_br(value):
    """Formata valor para padrão brasileiro: R$ ###.###.##0,00"""
    if value is None:
        value = 0
    try:
        # Converte para float se necessário
        if isinstance(value, str):
            value = float(value)
        
        # Formata com separador de milhares e vírgula decimal
        formatted = f"{value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        return f"R$ {formatted}"
    except (ValueError, TypeError):
        return "R$ 0,00"

def format_number_br(value):
    """Formata número para padrão brasileiro: ###.###.##0,00"""
    if value is None:
        value = 0
    try:
        # Converte para float se necessário
        if isinstance(value, str):
            value = float(value)
        
        # Formata com separador de milhares e vírgula decimal
        formatted = f"{value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        return formatted
    except (ValueError, TypeError):
        return "0,00"

def format_integer_br(value):
    """Formata número inteiro para padrão brasileiro: ###.###"""
    if value is None:
        value = 0
    try:
        # Converte para int se necessário
        if isinstance(value, str):
            value = int(float(value))
        elif isinstance(value, float):
            value = int(value)
        
        # Formata com separador de milhares
        formatted = f"{value:,}".replace(',', '.')
        return formatted
    except (ValueError, TypeError):
        return "0"

# Registra funções como filtros do Jinja2
app.jinja_env.filters['currency_br'] = format_currency_br
app.jinja_env.filters['number_br'] = format_number_br
app.jinja_env.filters['integer_br'] = format_integer_br

# Inicializa banco de dados, OAuth e executa backup inicial
db = Database()
oauth_manager = OAuthManager()

try:
    current_env = environment_manager.get_current_environment()
    db_path = Config.get_database_path()
    created, detail = perform_backup(db_path, current_env, force=False, max_hours=24)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Backup startup: criado={created} detalhe={detail}")
    # Inicia backups periódicos a cada 6h para garantir janela <24h mesmo com app aberto por longos períodos
    start_periodic_backups(db_path, current_env, interval_hours=6)
except Exception as e:
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Erro ao executar rotina de backup inicial: {e}")

@app.route('/')
def index():
    """Página principal do dashboard"""
    try:
        # Obtém dados do banco
        last_sync = db.get_last_sync()
        accounts = db.get_accounts_summary()
        statistics = db.get_statistics()
        recent_transactions = db.get_transactions(limit=10)
        
        # Verifica status OAuth
        oauth_status = oauth_manager.has_valid_connection()
        pending_mappings = db.count_unmapped_categories()
        return render_template('index.html',
                             last_sync=last_sync,
                             accounts=accounts,
                             statistics=statistics,
                             recent_transactions=recent_transactions,
                             oauth_connected=oauth_status,
                             oauth_manager=oauth_manager,
                             pending_mappings=pending_mappings)
    except Exception as e:
        flash(f'Erro ao carregar dados: {e}', 'error')
        return render_template('index.html', 
                             last_sync=None,
                             accounts=[],
                             statistics={},
                             recent_transactions=[],
                             oauth_connected=False,
                             pending_mappings=0)

@app.route('/sync', methods=['POST'])
def sync_account():
    """Sincroniza dados com Meu Pluggy com atualização forçada"""
    try:
        # Validação das configurações obrigatórias
        config_valid, missing_fields = settings_manager.validate_required_settings()
        if not config_valid:
            return jsonify({
                'success': False,
                'message': f'Configurações obrigatórias não preenchidas: {", ".join(missing_fields)}',
                'redirect': '/settings'
            })
        
        finance_app = FinanceApp()
        
        # Verifica se já tem conexão OAuth
        if oauth_manager.has_valid_connection():
            print("🚀 Iniciando sincronização com atualização forçada...")
            
            # Sincronização completa com atualização forçada
            success, message = finance_app.sync_existing_connection()
            
            if success:
                # Reconciliar categorias após sincronização completa
                new_cats = db.reconcile_category_mappings()
                notice = ''
                if new_cats:
                    notice = f" - {len(new_cats)} novas categorias aguardam classificação (De-Para)"
                flash(message + notice, 'success')
                return jsonify({
                    'success': True, 
                    'message': f'✅ {message}{notice}'
                })
            else:
                flash(f'Erro na sincronização: {message}', 'error')
                return jsonify({'success': False, 'message': message})
        else:
            # Precisa fazer OAuth primeiro
            return jsonify({
                'success': False, 
                'message': 'Nenhuma conexão OAuth configurada. Adicione conexões no painel de gerenciamento.', 
                'redirect': '/manage_connections'
            })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro na sincronização: {e}'})

@app.route('/start_oauth', methods=['POST'])
def start_oauth():
    """Inicia o processo OAuth"""
    try:
        # Validação das configurações obrigatórias
        config_valid, missing_fields = settings_manager.validate_required_settings()
        if not config_valid:
            return jsonify({
                'success': False,
                'message': f'Configurações obrigatórias não preenchidas: {", ".join(missing_fields)}. Acesse Configurações para preenchê-las.',
                'redirect': '/settings'
            })
        
        finance_app = FinanceApp()
        
        # Autentica
        if not finance_app.authenticate():
            return jsonify({'success': False, 'message': 'Erro na autenticação'})
        
        # Cria item OAuth
        response = requests.post(
            f"{finance_app.base_url}/items",
            headers={"Content-Type": "application/json", "X-API-KEY": finance_app.api_key},
            json={"connectorId": 200, "parameters": {}}
        )
        response.raise_for_status()
        
        item_data = response.json()
        item_id = item_data.get('id')
        
        # Salva item_id temporário
        oauth_manager.save_oauth_data(item_id=item_id, status="pending")
        
        # Aguarda URL OAuth
        for attempt in range(10):
            time.sleep(2)
            
            status_response = requests.get(
                f"{finance_app.base_url}/items/{item_id}",
                headers={"X-API-KEY": finance_app.api_key}
            )
            
            if status_response.status_code == 200:
                item_info = status_response.json()
                parameter = item_info.get('parameter')
                
                if parameter and 'data' in parameter:
                    oauth_url = parameter['data']
                    
                    # Salva URL OAuth
                    oauth_manager.save_oauth_data(
                        item_id=item_id,
                        status="pending",
                        oauth_url=oauth_url,
                        expires_at=parameter.get('expiresAt')
                    )
                    
                    return jsonify({
                        'success': True, 
                        'oauth_url': oauth_url,
                        'item_id': item_id,
                        'message': 'URL OAuth gerada com sucesso'
                    })
        
        return jsonify({'success': False, 'message': 'Timeout ao obter URL OAuth'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao iniciar OAuth: {e}'})

@app.route('/reset_oauth', methods=['POST'])
def reset_oauth():
    """Remove conexão OAuth para reconectar"""
    try:
        oauth_manager.clear_oauth_data()
        flash('Conexão OAuth removida. Configure novamente.', 'info')
        return jsonify({'success': True, 'message': 'OAuth resetado com sucesso'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao resetar OAuth: {e}'})

@app.route('/transactions')
def transactions():
    """Página de transações com filtros e informações de conexão"""
    try:
        # Parâmetros de filtro - suporte a valores múltiplos
        account_id = request.args.getlist('account_id')  # Lista de IDs
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        category = request.args.get('category')  # Manter por compatibilidade
        user_category = request.args.getlist('user_category')  # Lista de categorias
        user_subcategory = request.args.getlist('user_subcategory')  # Lista de subcategorias
        modification_start_date = request.args.get('modification_start_date')
        modification_end_date = request.args.get('modification_end_date')
        verification_filter = request.args.getlist('verification_filter')  # Lista de status
        type_filter = request.args.getlist('type_filter')  # Lista de tipos de transação
        limit = int(request.args.get('limit', 100))

        # Busca transações com informações de conexão
        transactions_list = db.get_transactions_with_connection_info(
            limit=limit,
            account_id=account_id if account_id else None,
            connection_id=None,
            start_date=start_date,
            end_date=end_date,
            category=category,
            user_category=user_category if user_category else None,
            user_subcategory=user_subcategory if user_subcategory else None,
            modification_start_date=modification_start_date,
            modification_end_date=modification_end_date,
            verification_filter=verification_filter if verification_filter else None,
            type_filter=type_filter if type_filter else None
        )

        # Dados auxiliares para filtros e exibição
        accounts = db.get_accounts_summary()
        connections = oauth_manager.get_all_connections()
        categories = db.get_categories()

        # Categorias de usuário únicas
        all_user_categories = db.get_user_categories()
        user_categories_list = list(set([cat['name'] for cat in all_user_categories if cat['name']]))
        user_subcategories_list = list(set([cat['subcategory'] for cat in all_user_categories if cat['subcategory']]))

        # Estatísticas gerais e nomes dos usuários para divisão
        all_transactions = db.get_transactions_with_connection_info(limit=10000)
        division_names = db.get_division_user_names()

        return render_template(
            'transactions.html',
            transactions=transactions_list,
            all_transactions=all_transactions,
            accounts=accounts,
            connections=connections,
            categories=categories,
            user_categories=user_categories_list,
            user_subcategories=user_subcategories_list,
            division_names=division_names,
            filters={
                'account_id': account_id,
                'connection_id': None,
                'start_date': start_date,
                'end_date': end_date,
                'category': category,
                'user_category': user_category,
                'user_subcategory': user_subcategory,
                'modification_start_date': modification_start_date,
                'modification_end_date': modification_end_date,
                'verification_filter': verification_filter,
                'type_filter': type_filter,
                'limit': limit,
            },
        )
    except Exception as e:
        flash(f'Erro ao carregar transações: {e}', 'error')
        return render_template(
            'transactions.html',
            transactions=[],
            accounts=[],
            connections={},
            filters={},
        )

@app.route('/transactions/<transaction_id>/split', methods=['POST'])
def update_transaction_split(transaction_id):
    """Atualiza percentuais de divisão da transação via AJAX (JSON)."""
    try:
        data = request.get_json(force=True)
        user1_percent = data.get('user1_percent')
        user2_percent = data.get('user2_percent')
        ok = db.update_transaction_split(transaction_id, user1_percent, user2_percent)
        return jsonify({'success': ok})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao atualizar divisão: {e}'})

@app.route('/edit_transaction/<transaction_id>', methods=['GET', 'POST'])
def edit_transaction(transaction_id):
    """Edita uma transação específica - suporta tanto modal quanto página completa"""
    try:
        if request.method == 'GET':
            # Busca a transação para edição
            transaction = db.get_transaction_by_id(transaction_id)
            if not transaction:
                if request.is_json or request.headers.get('Content-Type') == 'application/json':
                    return jsonify({'success': False, 'message': 'Transação não encontrada'})
                flash('Transação não encontrada', 'error')
                return redirect(url_for('transactions'))
            
            # Busca contas para o dropdown
            accounts = db.get_accounts_summary()
            categories = db.get_categories()
            
            # Se é uma requisição AJAX, retorna JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': True,
                    'transaction': transaction,
                    'accounts': accounts,
                    'categories': categories
                })
            
            # Senão, retorna a página normal
            return render_template('edit_transaction.html', 
                                 transaction=transaction,
                                 accounts=accounts,
                                 categories=categories)
        
        elif request.method == 'POST':
            # Dados do formulário
            amount = float(request.form.get('amount', 0))
            description = request.form.get('description', '').strip()
            category = request.form.get('category', '').strip()
            transaction_date = request.form.get('transaction_date', None)  # Pode ser None se não foi alterada
            account_id = request.form.get('account_id', '')
            transaction_type = request.form.get('type', 'DEBIT')  # Correção: usar 'type' ao invés de 'transaction_type'
            
            # Novos campos de categoria de usuário
            user_category = request.form.get('user_category', '').strip()
            user_subcategory = request.form.get('user_subcategory', '').strip()
            
            # Valida dados obrigatórios
            if not description:
                message = 'Descrição é obrigatória'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': message})
                flash(message, 'error')
                return redirect(url_for('edit_transaction', transaction_id=transaction_id))
            
            # Se transaction_date é None, busca a data atual da transação
            if transaction_date is None or transaction_date == '':
                current_transaction = db.get_transaction_by_id(transaction_id)
                if current_transaction:
                    transaction_date = current_transaction.get('transaction_date', '')
                else:
                    message = 'Transação não encontrada'
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({'success': False, 'message': message})
                    flash(message, 'error')
                    return redirect(url_for('edit_transaction', transaction_id=transaction_id))
            
            if not transaction_date:
                message = 'Data da transação é obrigatória'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': message})
                flash(message, 'error')
                return redirect(url_for('edit_transaction', transaction_id=transaction_id))
            
            # Atualiza a transação
            success = db.update_transaction(
                transaction_id=transaction_id,
                amount=amount,
                description=description,
                category=category,
                transaction_date=transaction_date,
                account_id=account_id,
                transaction_type=transaction_type
            )
            
            # Atualiza as categorias de usuário se a transação foi atualizada com sucesso
            if success and (user_category or user_subcategory):
                category_success = db.update_transaction_category(
                    transaction_id=transaction_id,
                    user_category=user_category if user_category else None,
                    user_subcategory=user_subcategory if user_subcategory else None
                )
                if not category_success:
                    print(f"⚠️ Aviso: Erro ao atualizar categorias de usuário para transação {transaction_id}")
            
            if success:
                message = 'Transação atualizada com sucesso!'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': True, 'message': message})
                flash(message, 'success')
            else:
                message = 'Erro ao atualizar transação'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': message})
                flash(message, 'error')
            
            return redirect(url_for('transactions'))
    except Exception as e:
        message = f'Erro ao processar edição: {e}'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': message})
        flash(message, 'error')
        return redirect(url_for('transactions'))

@app.route('/division', methods=['GET'])
def division():
    """Página de Divisão de percentuais por conta (Usuário 1 e Usuário 2)."""
    try:
        user_names = db.get_division_user_names()
        accounts_with_splits = db.get_accounts_with_splits()
        return render_template('division.html', user_names=user_names, accounts=accounts_with_splits)
    except Exception as e:
        flash(f'Erro ao carregar Divisão: {e}', 'error')
        return render_template('division.html', user_names={'user1_name': 'Usuário 1', 'user2_name': 'Usuário 2'}, accounts=[])

@app.route('/api/division/names', methods=['GET', 'POST'])
def division_names():
    """GET: retorna nomes; POST: atualiza nomes dos usuários da Divisão."""
    try:
        if request.method == 'GET':
            return jsonify({'success': True, **db.get_division_user_names()})
        else:
            data = request.get_json(force=True)
            u1 = data.get('user1_name', 'Usuário 1')
            u2 = data.get('user2_name', 'Usuário 2')
            ok = db.update_division_user_names(u1, u2)
            return jsonify({'success': ok})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro: {e}'})

@app.route('/api/division/split', methods=['POST'])
def division_split_save():
    """Salva percentuais de uma conta. Espera JSON: { account_id, user1_percent, user2_percent? }"""
    try:
        data = request.get_json(force=True)
        account_id = data.get('account_id')
        user1_percent = data.get('user1_percent', 50)
        user2_percent = data.get('user2_percent', None)
        if not account_id:
            return jsonify({'success': False, 'message': 'account_id é obrigatório'})
        ok = db.upsert_account_split(account_id, user1_percent, user2_percent)
        return jsonify({'success': ok})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro: {e}'})

@app.route('/toggle_transaction_verification', methods=['POST'])
def toggle_transaction_verification():
    """Toggle do status de verificação de uma transação via AJAX"""
    try:
        data = request.get_json()
        transaction_id = data.get('transaction_id')
        verified_status = data.get('verified')
        
        if not transaction_id:
            return jsonify({'success': False, 'message': 'ID da transação é obrigatório'})
        
        success = db.update_transaction_verification(transaction_id, 1 if verified_status else 0)
        
        if success:
            return jsonify({
                'success': True, 
                'message': f'Transação {"marcada como verificada" if verified_status else "desmarcada como verificada"}'
            })
        else:
            return jsonify({'success': False, 'message': 'Erro ao atualizar status de verificação'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao processar verificação: {e}'})

@app.route('/toggle_transaction_ignore', methods=['POST'])
def toggle_transaction_ignore():
    """Toggle do status de ignorar de uma transação via AJAX"""
    try:
        data = request.get_json()
        transaction_id = data.get('transaction_id')
        ignore_status = data.get('ignore')
        
        if not transaction_id:
            return jsonify({'success': False, 'message': 'ID da transação é obrigatório'})
        
        success = db.update_transaction_ignore_status(transaction_id, 1 if ignore_status else 0)
        
        if success:
            return jsonify({
                'success': True, 
                'message': f'Transação {"marcada para ignorar" if ignore_status else "desmarcada para ignorar"}'
            })
        else:
            return jsonify({'success': False, 'message': 'Erro ao atualizar status de ignorar'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao processar status de ignorar: {e}'})

@app.route('/transactions/<transaction_id>/update-category', methods=['POST'])
def update_transaction_category_inline(transaction_id):
    """Atualiza categoria/subcategoria de uma transação via edição inline"""
    try:
        # Verificar se a transação está verificada (não pode ser editada)
        transaction = db.get_transaction_by_id(transaction_id)
        if not transaction:
            return jsonify({'success': False, 'message': 'Transação não encontrada'})
        
        if transaction.get('verified', 0) == 1:
            return jsonify({'success': False, 'message': 'Transação verificada não pode ser editada'})
        
        # Obter dados do formulário
        user_category = request.form.get('user_category', '').strip()
        user_subcategory = request.form.get('user_subcategory', '').strip()
        
        # Atualizar as categorias
        success = db.update_transaction_category(
            transaction_id=transaction_id,
            user_category=user_category if user_category else None,
            user_subcategory=user_subcategory if user_subcategory else None
        )
        
        if success:
            return jsonify({
                'success': True, 
                'message': 'Categoria atualizada com sucesso'
            })
        else:
            return jsonify({'success': False, 'message': 'Erro ao atualizar categoria'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao atualizar categoria: {e}'})

@app.route('/accounts')
def accounts():
    """Página de contas"""
    try:
        accounts_list = db.get_accounts_summary()
        account_types = db.get_account_types()
        return render_template('accounts.html', accounts=accounts_list, account_types=account_types)
    except Exception as e:
        flash(f'Erro ao carregar contas: {e}', 'error')
        return render_template('accounts.html', accounts=[], account_types=[])

@app.route('/accounts/create', methods=['GET', 'POST'])
def create_account():
    """Criar nova conta manual"""
    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form
            
            name = data.get('name', '').strip()
            account_type = data.get('type', '').strip()
            subtype = data.get('subtype', '').strip() or None
            balance = float(data.get('balance', 0))
            currency_code = data.get('currency_code', 'BRL').strip()
            
            if not name:
                return jsonify({'success': False, 'message': 'Nome da conta é obrigatório'})
            
            if not account_type:
                return jsonify({'success': False, 'message': 'Tipo da conta é obrigatório'})
            
            account_id = db.create_manual_account(name, account_type, subtype, balance, currency_code)
            
            if account_id:
                return jsonify({'success': True, 'account_id': account_id, 'message': 'Conta criada com sucesso!'})
            else:
                return jsonify({'success': False, 'message': 'Erro ao criar conta'})
                
        except ValueError as e:
            return jsonify({'success': False, 'message': 'Valor inválido para saldo'})
        except Exception as e:
            return jsonify({'success': False, 'message': f'Erro inesperado: {e}'})
    
    # GET request - mostrar formulário
    account_types = db.get_account_types()
    return render_template('create_account.html', account_types=account_types)

@app.route('/accounts/<account_id>/edit', methods=['GET', 'POST'])
def edit_account(account_id):
    """Editar conta manual"""
    if request.method == 'POST':
        try:
            if request.is_json:
                data = request.get_json()
            else:
                data = request.form.to_dict()
            
            # Remover campos vazios
            update_data = {}
            for key, value in data.items():
                if key in ['name', 'type', 'subtype', 'currency_code'] and value.strip():
                    update_data[key] = value.strip()
                elif key == 'balance':
                    update_data[key] = float(value)
            
            if not update_data:
                return jsonify({'success': False, 'message': 'Nenhum dado para atualizar'})
            
            success = db.update_manual_account(account_id, **update_data)
            
            if success:
                if request.is_json:
                    return jsonify({'success': True, 'message': 'Conta atualizada com sucesso!'})
                else:
                    flash('Conta atualizada com sucesso!', 'success')
                    return redirect(url_for('accounts'))
            else:
                if request.is_json:
                    return jsonify({'success': False, 'message': 'Erro ao atualizar conta ou conta não é manual'})
                else:
                    flash('Erro ao atualizar conta ou conta não é manual', 'error')
                    return redirect(url_for('accounts'))
                
        except ValueError as e:
            message = 'Valor inválido para saldo'
            if request.is_json:
                return jsonify({'success': False, 'message': message})
            else:
                flash(message, 'error')
                return redirect(url_for('accounts'))
        except Exception as e:
            message = f'Erro inesperado: {e}'
            if request.is_json:
                return jsonify({'success': False, 'message': message})
            else:
                flash(message, 'error')
                return redirect(url_for('accounts'))
    
    # GET request - mostrar dados da conta
    account = db.get_account_by_id(account_id)
    if not account:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Conta não encontrada'})
        else:
            flash('Conta não encontrada', 'error')
            return redirect(url_for('accounts'))
    
    if not account['is_manual']:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Apenas contas manuais podem ser editadas'})
        else:
            flash('Apenas contas manuais podem ser editadas', 'error')
            return redirect(url_for('accounts'))
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'account': account})
    else:
        account_types = db.get_account_types()
        return render_template('edit_account.html', account=account, account_types=account_types)

@app.route('/accounts/<account_id>/delete', methods=['POST'])
def delete_account(account_id):
    """Excluir conta manual e suas transações"""
    try:
        success, message = db.delete_manual_account_with_transactions(account_id)
        
        if request.is_json:
            return jsonify({'success': success, 'message': message})
        else:
            if success:
                flash(message, 'success')
            else:
                flash(message, 'error')
            return redirect(url_for('accounts'))
            
    except Exception as e:
        message = f'Erro inesperado: {e}'
        if request.is_json:
            return jsonify({'success': False, 'message': message})
        else:
            flash(message, 'error')
            return redirect(url_for('accounts'))

@app.route('/accounts/<account_id>/transaction-count', methods=['GET'])
def get_account_transaction_count(account_id):
    """Obter contagem de transações de uma conta"""
    try:
        count = db.get_account_transaction_count(account_id)
        return jsonify({'success': True, 'transaction_count': count})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro: {e}'})

@app.route('/api/statistics')
def api_statistics():
    """API para estatísticas (para atualização dinâmica)"""
    try:
        stats = db.get_statistics()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/sync_status')
def api_sync_status():
    """API para verificar status da última sincronização"""
    try:
        last_sync = db.get_last_sync()
        return jsonify(last_sync or {})
    except Exception as e:
        return jsonify({'error': str(e)})

# Função para executar sincronização completa (para uso interno)
def run_full_sync():
    """Executa sincronização completa e salva no banco"""
    try:
        finance_app = FinanceApp()
        
        # Autentica
        if not finance_app.authenticate():
            return False, "Erro na autenticação"
        
        # Cria conexão OAuth (seria necessário ter item_id salvo)
        # Por simplicidade, vamos simular dados
        
        # Em produção, você salvaria o item_id após o primeiro OAuth
        # e reutilizaria para sincronizações futuras
        
        return True, "Sincronização simulada com sucesso"
        
    except Exception as e:
        return False, f"Erro na sincronização: {e}"

@app.route('/manage_connections')
def manage_connections():
    """Página para gerenciar múltiplas conexões OAuth"""
    summary = oauth_manager.get_connections_summary()
    return render_template('manage_connections.html', 
                         connections_data=summary)

@app.route('/update_data_since/<item_id>', methods=['POST'])
def update_data_since(item_id):
    """Atualiza campo 'dados desde' para limitar importação de transações futuras."""
    try:
        data = request.get_json(force=True)
        data_since = data.get('data_since') or None
        # Permite limpar enviando vazio
        if data_since == '':
            data_since = None
        success = oauth_manager.update_data_since(item_id, data_since)
        if success:
            return jsonify({'success': True, 'message': 'Filtro atualizado'})
        return jsonify({'success': False, 'message': 'Erro ao atualizar filtro'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro: {e}'})

@app.route('/add_connection', methods=['GET', 'POST'])
def add_connection():
    """Adiciona nova conexão OAuth"""
    if request.method == 'POST':
        try:
            # Aceita tanto JSON quanto form data
            if request.is_json:
                data = request.get_json()
                bank_name = data.get('bank_name', '').strip()
            else:
                bank_name = request.form.get('bank_name', '').strip()
            
            if not bank_name:
                return jsonify({'success': False, 'message': 'Nome do banco é obrigatório'})
            
            finance_app = FinanceApp()
            result = finance_app.create_oauth_connection_with_name(bank_name)
            
            if result and len(result) == 2:
                item_id, oauth_url = result
                return jsonify({
                    'success': True, 
                    'item_id': item_id,
                    'oauth_url': oauth_url,
                    'message': f'Conexão criada para {bank_name}'
                })
            else:
                return jsonify({'success': False, 'message': 'Erro ao criar conexão OAuth'})
        
        except Exception as e:
            return jsonify({'success': False, 'message': f'Erro: {e}'})
    
    return render_template('add_connection.html')

@app.route('/remove_connection/<item_id>', methods=['POST'])
def remove_connection(item_id):
    """Remove uma conexão OAuth específica"""
    try:
        data = request.get_json() if request.is_json else {}
        remove_data = data.get('remove_data', False)  # Se deve remover também as transações e contas
        
        # Busca informações da conexão antes de remover
        connection_info = oauth_manager.get_connection_info(item_id)
        bank_name = connection_info.get('bank_name', 'Conexão') if connection_info else 'Conexão'
        
        # Remove a conexão OAuth
        success = oauth_manager.remove_connection(item_id)
        
        if success and remove_data:
            # Remove também contas e transações associadas a esta conexão específica
            try:
                import sqlite3
                conn = sqlite3.connect('data/finance_app.db')
                cursor = conn.cursor()
                
                # Conta quantos registros serão removidos antes (usando connection_name)
                cursor.execute('SELECT COUNT(*) FROM transactions WHERE connection_name = ?', (bank_name,))
                transactions_count = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM accounts WHERE connection_name = ?', (bank_name,))
                accounts_count = cursor.fetchone()[0]
                
                # Remove transações apenas desta conexão específica
                cursor.execute('DELETE FROM transactions WHERE connection_name = ?', (bank_name,))
                transactions_removed = cursor.rowcount
                
                # Remove contas apenas desta conexão específica  
                cursor.execute('DELETE FROM accounts WHERE connection_name = ?', (bank_name,))
                accounts_removed = cursor.rowcount
                
                conn.commit()
                conn.close()
                
                if accounts_removed > 0 or transactions_removed > 0:
                    return jsonify({
                        'success': True, 
                        'message': f'{accounts_removed} contas e {transactions_removed} transações da conexão "{bank_name}" foram removidas permanentemente.'
                    })
                else:
                    return jsonify({
                        'success': True, 
                        'message': f'Conexão "{bank_name}" removida. Nenhum dado financeiro foi encontrado para esta conexão.'
                    })
            except Exception as e:
                return jsonify({
                    'success': True, 
                    'message': f'Conexão "{bank_name}" removida, mas erro ao remover dados: {e}'
                })
        elif success:
            return jsonify({
                'success': True, 
                'message': f'Conexão "{bank_name}" removida com sucesso. Dados financeiros foram mantidos no histórico.'
            })
        else:
            return jsonify({'success': False, 'message': f'Conexão "{bank_name}" não encontrada'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro: {e}'})

@app.route('/update_connection_name/<item_id>', methods=['POST'])
def update_connection_name(item_id):
    """Atualiza nome de uma conexão"""
    try:
        data = request.get_json()
        new_name = data.get('bank_name', '').strip()
        
        if not new_name:
            return jsonify({'success': False, 'message': 'Nome não pode estar vazio'})
        
        success = oauth_manager.update_connection_name(item_id, new_name)
        if success:
            return jsonify({'success': True, 'message': 'Nome atualizado com sucesso'})
        else:
            return jsonify({'success': False, 'message': 'Conexão não encontrada'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro: {e}'})

@app.route('/check_oauth_status/<item_id>')
def check_oauth_status(item_id):
    """Verifica status de uma conexão OAuth específica"""
    try:
        finance_app = FinanceApp()
        
        if not finance_app.authenticate():
            return jsonify({'success': False, 'message': 'Erro na autenticação'})
        
        # Verifica status do item no Pluggy
        response = requests.get(
            f"{finance_app.base_url}/items/{item_id}",
            headers={"X-API-KEY": finance_app.api_key}
        )
        
        if response.status_code == 200:
            item_data = response.json()
            status = item_data.get('status')
            
            print(f"🔍 Debug - Status retornado da API: {status}")
            print(f"🔍 Debug - Item data: {item_data}")
            
            if status in ['CONNECTED', 'UPDATED']:
                # Atualiza status local
                oauth_manager.update_status(item_id, 'active')
                connection_info = oauth_manager.get_connection_info(item_id)
                bank_name = connection_info.get('bank_name', 'Conta') if connection_info else 'Conta'
                
                return jsonify({
                    'success': True, 
                    'status': 'completed',
                    'message': f'✅ {bank_name} conectado com sucesso!'
                })
            elif status in ['WAITING_USER_INPUT', 'LOGIN_IN_PROGRESS', 'UPDATING']:
                return jsonify({
                    'success': True, 
                    'status': 'pending',
                    'message': 'Aguardando autorização do usuário...'
                })
            elif status in ['LOGIN_ERROR', 'OUTDATED']:
                return jsonify({
                    'success': True, 
                    'status': 'error',
                    'message': 'Erro na autorização. Tente novamente.'
                })
            else:
                return jsonify({
                    'success': True, 
                    'status': 'pending',
                    'message': f'Status: {status}'
                })
        else:
            return jsonify({'success': False, 'message': 'Erro ao verificar status'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro: {e}'})

@app.route('/sync_connection/<item_id>', methods=['POST'])
def sync_connection(item_id):
    """Força sincronização de uma conexão específica"""
    try:
        # Validação das configurações obrigatórias
        config_valid, missing_fields = settings_manager.validate_required_settings()
        if not config_valid:
            return jsonify({
                'success': False,
                'message': f'Configurações obrigatórias não preenchidas: {", ".join(missing_fields)}. Acesse Configurações para preenchê-las.',
                'redirect': '/settings'
            })
        
        finance_app = FinanceApp()
        result = finance_app.sync_single_connection(item_id)
        
        if result:
            new_cats = db.reconcile_category_mappings()
            stats = result.get('stats', {})
            new_notice = f"\n⚠️ {len(new_cats)} novas categorias aguardam De-Para" if new_cats else ''
            if stats:
                accounts_msg = f"{stats.get('accounts_inserted', 0)} novas, {stats.get('accounts_updated', 0)} atualizadas, {stats.get('accounts_unchanged', 0)} inalteradas"
                transactions_msg = f"{stats.get('transactions_inserted', 0)} novas, {stats.get('transactions_updated', 0)} atualizadas, {stats.get('transactions_unchanged', 0)} inalteradas"
                message = f"Sincronização incremental concluída{new_notice}\n"
                message += f"💳 Contas: {accounts_msg}\n"
                message += f"💰 Transações: {transactions_msg}"
            else:
                message = 'Sincronização iniciada com sucesso' + new_notice
            return jsonify({
                'success': True, 
                'message': message,
                'accounts': result.get('accounts', 0),
                'transactions': result.get('transactions', 0)
            })
        else:
            return jsonify({'success': False, 'message': 'Erro na sincronização'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro: {e}'})

@app.route('/connection_stats/<item_id>')
def connection_stats(item_id):
    """Retorna estatísticas de uma conexão específica"""
    try:
        import sqlite3
        conn = sqlite3.connect('data/finance_app.db')
        cursor = conn.cursor()
        
        # Conta contas
        cursor.execute('SELECT COUNT(*) FROM accounts WHERE item_id = ?', (item_id,))
        accounts_count = cursor.fetchone()[0]
        
        # Conta transações
        cursor.execute('SELECT COUNT(*) FROM transactions WHERE item_id = ?', (item_id,))
        transactions_count = cursor.fetchone()[0]
        
        # Última transação
        cursor.execute('SELECT MAX(date) FROM transactions WHERE item_id = ?', (item_id,))
        last_transaction = cursor.fetchone()[0]
        
        # Saldo total das contas
        cursor.execute('SELECT SUM(balance) FROM accounts WHERE item_id = ?', (item_id,))
        total_balance = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return jsonify({
            'success': True,
            'accounts': accounts_count,
            'transactions': transactions_count,
            'last_transaction': last_transaction,
            'total_balance': total_balance
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro: {e}'})

@app.route('/transactions/create', methods=['POST'])
def create_transaction():
    """Criar nova transação manual"""
    try:
        data = request.get_json() if request.is_json else request.form
        
        account_id = data.get('account_id', '').strip()
        amount = float(data.get('amount', 0))
        description = data.get('description', '').strip()
        transaction_date = data.get('transaction_date', '').strip()
        category = data.get('category', '').strip() or None
        transaction_type = data.get('type', '').strip()
        
        # Validar campos obrigatórios
        if not account_id:
            return jsonify({'success': False, 'message': 'Conta é obrigatória'})
        
        if not description:
            return jsonify({'success': False, 'message': 'Descrição é obrigatória'})
        
        if not transaction_date:
            return jsonify({'success': False, 'message': 'Data da transação é obrigatória'})
        
        if not transaction_type or transaction_type not in ['CREDIT', 'DEBIT']:
            return jsonify({'success': False, 'message': 'Tipo da transação deve ser CREDIT ou DEBIT'})
        
        # Verificar se a conta existe
        account = db.get_account_by_id(account_id)
        if not account:
            return jsonify({'success': False, 'message': 'Conta não encontrada'})
        
        # Criar a transação
        transaction_id = db.create_manual_transaction(
            account_id=account_id,
            amount=amount,
            description=description,
            transaction_date=transaction_date,
            category=category,
            transaction_type=transaction_type
        )
        
        if transaction_id:
            return jsonify({
                'success': True, 
                'transaction_id': transaction_id,
                'message': 'Transação criada com sucesso!'
            })
        else:
            return jsonify({'success': False, 'message': 'Erro ao criar transação'})
            
    except ValueError as e:
        return jsonify({'success': False, 'message': f'Valor inválido: {e}'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro inesperado: {e}'})

@app.route('/transactions/<transaction_id>/delete', methods=['POST'])
def delete_transaction(transaction_id):
    """Excluir transação"""
    try:
        success, message = db.delete_transaction(transaction_id)
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro inesperado: {e}'})

# ========================================
# ROTAS PARA GERENCIAR CATEGORIAS
# ========================================

@app.route('/categories')
def categories():
    """Página de gerenciamento de categorias"""
    try:
        # Buscar categorias agrupadas por tipo
        credit_categories = db.get_categories_grouped('CREDIT')
        debit_categories = db.get_categories_grouped('DEBIT')
        
        return render_template('categories.html',
                             credit_categories=credit_categories,
                             debit_categories=debit_categories)
                             
    except Exception as e:
        flash(f'Erro ao carregar categorias: {e}', 'error')
        return render_template('categories.html',
                             credit_categories={},
                             debit_categories={})

@app.route('/categories/create', methods=['POST'])
def create_category():
    """Criar nova categoria/subcategoria"""
    try:
        data = request.get_json() if request.is_json else request.form
        
        name = data.get('name', '').strip()
        subcategory = data.get('subcategory', '').strip() or None
        transaction_type = data.get('transaction_type', '').strip()
        description = data.get('description', '').strip() or None
        color = data.get('color', '').strip() or None
        icon = data.get('icon', '').strip() or None
        
        # Validações
        if not name:
            return jsonify({'success': False, 'message': 'Nome da categoria é obrigatório'})
        
        if transaction_type not in ['CREDIT', 'DEBIT']:
            return jsonify({'success': False, 'message': 'Tipo deve ser CREDIT ou DEBIT'})
        
        category_id = db.create_user_category(
            name=name,
            subcategory=subcategory,
            transaction_type=transaction_type,
            description=description,
            color=color,
            icon=icon
        )
        
        if category_id:
            return jsonify({
                'success': True,
                'category_id': category_id,
                'message': 'Categoria criada com sucesso!'
            })
        else:
            return jsonify({'success': False, 'message': 'Erro ao criar categoria (pode já existir)'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro inesperado: {e}'})

@app.route('/categories/<int:category_id>/edit', methods=['POST'])
def edit_category(category_id):
    """Editar categoria existente"""
    try:
        data = request.get_json() if request.is_json else request.form
        
        # Monta dict com campos a serem atualizados
        update_data = {}
        for field in ['name', 'subcategory', 'transaction_type', 'description', 'color', 'icon']:
            if field in data and data[field]:
                update_data[field] = data[field].strip()
        
        if 'is_active' in data:
            update_data['is_active'] = 1 if data['is_active'] else 0
        
        if not update_data:
            return jsonify({'success': False, 'message': 'Nenhum campo para atualizar'})
        
        success = db.update_user_category(category_id, **update_data)
        
        if success:
            return jsonify({'success': True, 'message': 'Categoria atualizada com sucesso!'})
        else:
            return jsonify({'success': False, 'message': 'Categoria não encontrada ou erro na atualização'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro inesperado: {e}'})

@app.route('/categories/<int:category_id>/delete', methods=['POST'])
def delete_category(category_id):
    """Excluir categoria"""
    try:
        success, message = db.delete_user_category(category_id)
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro inesperado: {e}'})

@app.route('/api/categories')
def api_categories():
    """API para buscar categorias (para uso em dropdowns)"""
    try:
        transaction_type = request.args.get('type')  # 'CREDIT', 'DEBIT' ou None
        categories = db.get_user_categories(transaction_type)
        
        return jsonify({
            'success': True,
            'categories': categories
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro: {e}'})

@app.route('/categories/populate_defaults', methods=['POST'])
def populate_default_categories():
    """Popula categorias padrão no banco de dados"""
    try:
        success = db.populate_default_categories()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Categorias padrão criadas com sucesso!'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Erro ao criar categorias padrão'
            })
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro inesperado: {e}'})

# ========================================
# DE-PARA DE CATEGORIAS (API -> Usuário)
# ========================================
@app.route('/category_mappings')
def category_mappings_page():
    """Página de gestão de De-Para entre categorias da API e categorias do usuário."""
    try:
        new_cats = db.reconcile_category_mappings()
        mappings = db.get_category_mappings()
        user_categories = db.get_user_categories()
        return render_template('category_mappings.html',
                               mappings=mappings,
                               user_categories=user_categories,
                               new_count=len(new_cats))
    except Exception as e:
        flash(f'Erro ao carregar De-Para: {e}', 'error')
        return render_template('category_mappings.html', mappings=[], user_categories=[], new_count=0)

@app.route('/api/category_mappings', methods=['GET'])
def api_get_category_mappings():
    try:
        return jsonify({'success': True, 'mappings': db.get_category_mappings(), 'pending': db.count_unmapped_categories()})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro: {e}'})

@app.route('/api/category_mappings/reconcile', methods=['POST'])
def api_reconcile_category_mappings():
    try:
        new_cats = db.reconcile_category_mappings()
        return jsonify({'success': True, 'new': new_cats, 'pending': db.count_unmapped_categories()})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro: {e}'})

@app.route('/api/category_mappings/update', methods=['POST'])
def api_update_category_mapping():
    try:
        data = request.get_json(force=True)
        source_category = data.get('source_category')
        transaction_type = data.get('transaction_type')
        mapped_user_category = data.get('mapped_user_category') or None
        mapped_user_subcategory = data.get('mapped_user_subcategory') or None
        ok = db.update_category_mapping(source_category, transaction_type, mapped_user_category, mapped_user_subcategory)
        return jsonify({'success': ok, 'pending': db.count_unmapped_categories()})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro: {e}'})

@app.route('/api/category_mappings/delete', methods=['POST'])
def api_delete_category_mapping():
    """Remove um mapeamento específico."""
    try:
        data = request.get_json(force=True)
        source_category = data.get('source_category')
        transaction_type = data.get('transaction_type')
        if not source_category:
            return jsonify({'success': False, 'message': 'source_category obrigatório'}), 400
        ok = db.delete_category_mapping(source_category, transaction_type)
        return jsonify({'success': ok, 'pending': db.count_unmapped_categories()})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro: {e}'})

@app.route('/api/transactions/suggest_categories', methods=['POST'])
def api_suggest_categories():
    try:
        similarity = request.args.get('similarity', default=0.88, type=float)
        result = db.suggest_categories_for_transactions(similarity_threshold=similarity, persist=False)
        return jsonify({
            'success': True,
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'stats': result.get('stats', {}),
            'suggestions': result.get('suggestions', [])
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ========================================
# CONFIGURAÇÕES DO SISTEMA
# ========================================

@app.route('/settings', methods=['GET', 'POST'])
def settings_page():
    """Página de configurações do sistema"""
    if request.method == 'POST':
        try:
            # Obtém os dados do formulário
            flask_secret_key = request.form.get('flask_secret_key', '').strip()
            pluggy_client_id = request.form.get('pluggy_client_id', '').strip()
            pluggy_client_secret = request.form.get('pluggy_client_secret', '').strip()
            
            # Valida se todos os campos estão preenchidos
            if not flask_secret_key or not pluggy_client_id or not pluggy_client_secret:
                flash('Todos os campos são obrigatórios!', 'error')
                return redirect(url_for('settings_page'))
            
            # Salva as configurações
            success = settings_manager.save_settings(
                flask_secret_key=flask_secret_key,
                pluggy_client_id=pluggy_client_id,
                pluggy_client_secret=pluggy_client_secret
            )
            
            if success:
                flash('Configurações salvas com sucesso!', 'success')
                
                # Atualiza a chave secreta do Flask na instância atual
                app.secret_key = flask_secret_key
                
                # Recarrega as configurações no módulo Config
                Config.reload_from_settings()
                
            else:
                flash('Erro ao salvar as configurações.', 'error')
                
        except Exception as e:
            flash(f'Erro inesperado: {e}', 'error')
        
        return redirect(url_for('settings_page'))
    
    # GET - Exibe a página
    try:
        # Carrega configurações atuais
        config = settings_manager.get_settings()
        config_valid, missing_fields = settings_manager.validate_required_settings()
        
        return render_template('settings.html', 
                             config=config,
                             config_valid=config_valid,
                             missing_fields=missing_fields,
                             settings_file=settings_manager.settings_file)
    except Exception as e:
        flash(f'Erro ao carregar configurações: {e}', 'error')
        return render_template('settings.html', 
                             config={'flask_secret_key': None, 'pluggy_client_id': None, 'pluggy_client_secret': None},
                             config_valid=False,
                             missing_fields=['FLASK_SECRET_KEY', 'PLUGGY_CLIENT_ID', 'PLUGGY_CLIENT_SECRET'],
                             settings_file=settings_manager.settings_file)

@app.route('/api/settings/validate', methods=['GET'])
def api_validate_settings():
    """API para validar se as configurações estão completas"""
    try:
        config_valid, missing_fields = settings_manager.validate_required_settings()
        return jsonify({
            'success': True,
            'config_valid': config_valid,
            'missing_fields': missing_fields
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro ao validar configurações: {e}'
        })

# ========================================
# GERENCIAMENTO DE AMBIENTE (PROD/DEV)
# ========================================

@app.route('/api/environment/switch', methods=['POST'])
def switch_environment():
    """API para alternar entre ambientes PROD e DEV"""
    try:
        success, old_env, new_env = environment_manager.switch_environment()
        
        if success:
            # Recarrega as configurações após mudança de ambiente
            Config.reload_from_settings()
            
            # Reinicializa o database com o novo caminho
            global db
            new_db_path = Config.get_database_path()
            print(f"🔄 Alterando banco: {db.db_path} → {new_db_path}")
            db = Database()
            print(f"✅ Novo banco inicializado: {db.db_path}")
            
            # Reinicializa o settings_manager com o novo arquivo
            global settings_manager
            from settings_manager import SettingsManager
            settings_manager = SettingsManager()
            
            return jsonify({
                'success': True,
                'message': f'Ambiente alterado de {old_env.upper()} para {new_env.upper()}',
                'old_environment': old_env,
                'new_environment': new_env,
                'environment_info': environment_manager.get_environment_info()
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Erro ao alternar ambiente'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro ao alternar ambiente: {e}'
        })

@app.route('/api/environment/info', methods=['GET'])
def get_environment_info():
    """API para obter informações do ambiente atual"""
    try:
        env_info = environment_manager.get_environment_info()
        # Adiciona informações de debug do banco atual
        env_info['current_db_path'] = db.db_path if db else 'N/A'
        env_info['accounts_count'] = len(db.get_accounts()) if db else 0
        
        return jsonify({
            'success': True,
            'environment_info': env_info
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erro ao obter informações do ambiente: {e}'
        })

def open_browser():
    """Abre o navegador automaticamente após um pequeno delay"""
    time.sleep(1.5)  # Aguarda o servidor iniciar
    webbrowser.open('http://localhost:5000')

if __name__ == '__main__':
    # Cria pasta de templates se não existir
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    os.makedirs('data', exist_ok=True)
    
    print("🌐 Finance App Web Server")
    print("=" * 40)
    print("🔗 Acesse: http://localhost:5000")
    print("📊 Dashboard com contas e transações")
    print("🔄 Sincronização com Meu Pluggy")
    print("🌐 Abrindo navegador automaticamente...")
    print("=" * 40)
    
    # Inicia thread para abrir o navegador apenas quando não estiver reloading
    # Evita abrir múltiplas janelas quando o Flask reloader reinicia
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        threading.Thread(target=open_browser, daemon=True).start()
    
    app.run(debug=True, host='0.0.0.0', port=5000)
