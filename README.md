# Finance App (Flask + Pluggy)

Aplicativo Flask para consolidar contas e transações via Open Finance usando a API Pluggy. Suporta múltiplas conexões, categorização e interface web simples.

---
## Visão Geral Rápida
1. Requisitos e preparação do ambiente Python
2. Clonar o repositório
3. Criar contas Pluggy (meu.pluggy.ai e dashboard.pluggy.ai)
4. Conectar instituições (dentro do trial de 14 dias)
5. Criar `.env` e inserir credenciais
6. Gerar `FLASK_SECRET_KEY`
7. Escolher ambiente (dev/prod)
8. Instalar dependências
9. Rodar aplicação
10. (Opcional) Reset / manutenção

---
## 1. Requisitos
- Python 3.11+
- Conta no portal do usuário final: `https://meu.pluggy.ai/`
- Conta no dashboard de desenvolvedores: `https://dashboard.pluggy.ai/`
- (Opcional) Ambiente virtual Python

Verifique a versão do Python:
```
python --version
```

---
## 2. Clonar o Repositório
```
git clone https://github.com/<seu-usuario>/<seu-repo>.git
```
```
cd <seu-repo>
```

---
## 3. Criar Conta em meu.pluggy.ai (Usuário Final)
Portal utilizado para autorizar e consolidar contas via Open Finance.
Passos:
1. Acesse `https://meu.pluggy.ai/`.
2. Crie a conta (e-mail + senha) e confirme se solicitado.
3. Após login clique em adicionar/conectar instituição.
4. Conecte TODAS as instituições desejadas dentro dos 14 dias de trial.
5. Repita até concluir suas conexões principais.

---
## 4. Criar Conta no Dashboard (Desenvolvedor)
Portal para registrar a aplicação e gerar credenciais.
1. Acesse `https://dashboard.pluggy.ai/`.
2. Crie a conta (Sign Up) e faça login.
3. Vá em Applications / Apps.
4. Clique em "Create Application".
5. Nome sugerido: `Finance App Local Dev`.
6. Salve e copie `Client ID` e `Client Secret` (guarde com segurança).

Importante (Trial 14 dias):
- Durante o trial: pode criar novas conexões normalmente.
- Após o trial: não poderá adicionar novas conexões no Finance APP; apenas sincronizar as existentes.
- Crie todas as conexões com as contas durante o periodo de 14 dias

---
## 5. Criar o Arquivo .env
Copie o arquivo `.env.example` e renomeie para `.env` na raiz do projeto:
```
copy .env.example .env
```

---
## 6. Gerar e Definir FLASK_SECRET_KEY
Gera uma chave segura para sessão Flask.
A chave assina cookies de sessão (integridade). Em produção deve ser forte e privada.
```
python generate_secret_key.py
```
Copie o valor e preencha em `FLASK_SECRET_KEY=` no `.env`.

---
## 7. Inserir Credenciais Pluggy
Preencha no `.env` os valores obtidos no dashboard:
```
PLUGGY_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
PLUGGY_CLIENT_SECRET=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```
Não coloque aspas.

---
## 8. (Opcional) Ajustar Ambiente e Banco
`APP_ENV` controla qual banco SQLite será usado:
- `development` => `data/finance_app_dev.db`
- `production`  => `data/finance_app_prod.db`

```
APP_ENV=development
```

(OPCIONAL) -> Caso deseja alterar o caminho do banco de dados, descomente em `.env`:
```
# DATABASE_PATH=data/meu_banco_custom.db
```

---
## 9. Criar e Ativar Ambiente Virtual (Recomendado)
Windows PowerShell:
```
python -m venv venv
```
```
venv\Scripts\Activate.ps1
```

---
## 10. Instalar Dependências
```
pip install -r requirements.txt
```

---
## 11. Executar a Aplicação
```
python app.py
```
Acesse: `http://localhost:5000`

Primeiro acesso criará automaticamente o banco referente ao ambiente.

---
## 12. Verificar Banco de Dados
- Dev: `data/finance_app_dev.db`
- Prod: `data/finance_app_prod.db`

(OPCIONAL) -> Caso deseje resetar o banco de dados (DEV), remova o arquivo do banco:
```
Remove-Item data\finance_app_dev.db
```
Depois rode novamente `python app.py`.

---
## 13. Como Funciona a Sincronização
O app usa o `PLUGGY_CLIENT_ID` e `PLUGGY_CLIENT_SECRET` para obter token temporário e então:
- Lista conexões criadas em `meu.pluggy.ai`
- Sincroniza contas, saldos e transações
- Armazena no SQLite local

A sincronização será feita através do meu.pluggy.ai. Realize o login em sua conta para poder sincronizar os dados.

Após o trial: apenas sincronização das conexões já existentes continua possível (não cria novas).

---
## 14. Estrutura do Projeto (Referência)
```
app.py                # Entrypoint Flask
finance_app.py        # Sincronização Pluggy
database.py           # Persistência SQLite
oauth_manager.py      # Gerenciamento de conexões OAuth (se aplicável)
config.py             # Config e seleção de ambiente
generate_secret_key.py# Utilitário geração chave
data/                 # Bancos SQLite
templates/            # HTML (Jinja2)
static/               # CSS / JS
```

---
## 15. FAQ Rápido
- Autenticação falhou: valide `Client ID` / `Client Secret` e se token não expirou.
- Sem novas transações: verifique se a conexão ainda é válida no `meu.pluggy.ai`.
---
