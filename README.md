# Finance App (Flask + Pluggy)

Aplicativo Flask para consolidar contas e transações via API Pluggy, com múltiplas conexões, categorização personalizada e interface web.

---
## Passo 1. Requisitos
- Python 3.11+
- Conta Pluggy (Client ID / Client Secret)
- (Opcional) Ambiente virtual isolado

## Passo 2. Clonar o Repositório
```
git clone https://github.com/<seu-usuario>/<seu-repo>.git
cd <seu-repo>
```

## Passo 3. Criar e Ativar Ambiente Virtual (Windows PowerShell)
```
python -m venv venv
venv\Scripts\Activate.ps1
```

## Passo 4. Instalar Dependências
```
pip install -r requirements.txt
```

## Passo 5. Criar Arquivo .env
```
copy .env.example .env
```

## Passo 6. Gerar FLASK_SECRET_KEY
A chave assina cookies de sessão (integridade). Em produção deve ser forte e privada.

```
python generate_secret_key.py
```
Copie o valor e coloque em `.env`:
```
FLASK_SECRET_KEY=<valor_gerado>
```

## Passo 7. Preencher Credenciais Pluggy
No `.env` edite:
```
PLUGGY_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
PLUGGY_CLIENT_SECRET=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

## Passo 8. Escolher Ambiente (Dev ou Prod)
No `.env` defina:
```
APP_ENV=development   # para desenvolvimento local
```
ou
```
APP_ENV=production    # para ambiente real / deploy
```
Diferenças automáticas:
- Banco de dados: 
	- development => `data/finance_app_dev.db`
	- production  => `data/finance_app_prod.db`
- (Sugestão futura) Debug desligado em produção (pode ser ajustado em `app.py`).

Override opcional manual do banco de dados (não obrigatório):
```
# DATABASE_PATH=data/meu_banco_custom.db
```

## Passo 9. Estrutura do Projeto (referência)
```
app.py               # Entrypoint Flask
finance_app.py       # Lógica de sincronização Pluggy
database.py          # Persistência / Migrações simples
oauth_manager.py     # Gerenciamento conexões OAuth
config.py            # Configurações e seleção de ambiente
generate_secret_key.py # Geração de chave segura
data/                # Bancos SQLite (ignorado no Git)
templates/           # HTML (Jinja2)
static/              # CSS / JS
```

## Passo 10. Rodar a Aplicação
```
python app.py
```
Acesse: http://localhost:5000

## Passo 11. Verificar Banco Criado
Após primeiro uso:
- Se dev: `data/finance_app_dev.db`
- Se prod: `data/finance_app_prod.db`
Se quiser resetar: apagar o arquivo correspondente.

## Passo 12. Limpeza / Reset Rápido (DEV)
Apagar banco e recriar vazio:
```
Remove-Item data\finance_app_dev.db
```
Depois rodar novamente `python app.py`.
