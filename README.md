# Finance App (Flask + Pluggy)

Aplicativo Flask para consolidar contas e transações via Open Finance usando a API Pluggy. Suporta múltiplas conexões, categorização e interface web simples.

---
## Visão Geral Rápida
1. Requisitos e preparação do ambiente Python
2. Clonar o repositório
3. Criar contas Pluggy (meu.pluggy.ai e dashboard.pluggy.ai)
4. Conectar instituições (dentro do trial de 14 dias)
5. Criar ambiente virtual Python
6. Instalar dependências
7. Executar aplicação
8. Configurar credenciais na interface web
9. (Opcional) Alternar entre ambientes PROD/DEV

---
## 1. Requisitos
- Python 3.11+
- Git
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
git clone https://github.com/RenatoMoratti/Finance-App
```
```
cd Finance-App
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
## 5. Criar e Ativar Ambiente Virtual (Recomendado)
Windows PowerShell:
```
python -m venv venv
```
```
venv\Scripts\Activate.ps1
```

---
## 6. Instalar Dependências
```
pip install -r requirements.txt
```

---
## 7. Executar a Aplicação
```
python app.py
```
Acesse: `http://localhost:5000`

Primeiro acesso criará automaticamente o banco referente ao ambiente.

---
## 8. Configurar Credenciais na Interface Web
Após executar a aplicação, configure as credenciais através da interface:

### 8.1. Acessar Configurações
1. Na aplicação web, clique no ícone **⚙️ Configurações** na barra de navegação
2. Ou acesse diretamente: `http://localhost:5000/settings`

### 8.2. Preencher Credenciais Obrigatórias
Preencha todos os campos necessários:

**FLASK_SECRET_KEY:**
- Chave secreta para criptografia Flask
- Clique no botão **"Gerar Flask Secret Key"** para criar uma automaticamente
- Ou insira uma string aleatória com pelo menos 32 caracteres

**PLUGGY_CLIENT_ID:**
- ID do cliente obtido no painel: `https://dashboard.pluggy.ai`
- Formato: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

**PLUGGY_CLIENT_SECRET:**
- Chave secreta obtida no painel: `https://dashboard.pluggy.ai`
- Formato: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

### 8.3. Salvar Configurações
- Clique em **"Salvar Configurações"**
- As credenciais serão armazenadas com segurança em formato JSON
- ✅ Configurações salvas com sucesso!

### 8.4. Alternar Entre Ambientes (PROD/DEV)
- Use o botão **DEV/PROD** no canto superior direito da navbar
- **DEV**: Ambiente de desenvolvimento (`data/finance_app_dev.db`)
- **PROD**: Ambiente de produção (`data/finance_app_prod.db`)
- Cada ambiente mantém credenciais e dados separados
- Confirme a mudança quando solicitado

---
## 9. Como Funciona a Sincronização
O app usa o `PLUGGY_CLIENT_ID` e `PLUGGY_CLIENT_SECRET` para obter token temporário e então:
- Lista conexões criadas em `meu.pluggy.ai`
- Sincroniza contas, saldos e transações
- Armazena no SQLite local

A sincronização será feita através do meu.pluggy.ai. Realize o login em sua conta para poder sincronizar os dados.

Após o trial: apenas sincronização das conexões já existentes continua possível (não cria novas).

---
## 10. FAQ Rápido
**❓ Autenticação falhou:**
- Valide `Client ID` / `Client Secret` nas Configurações
- Verifique se as credenciais estão corretas no dashboard.pluggy.ai

**❓ Sem novas transações:**
- Verifique se a conexão ainda é válida no `meu.pluggy.ai`
- Sincronize novamente através da interface

**❓ Perdeu as configurações:**
- Acesse `/settings` para reconfigurar credenciais
- Use o botão "Gerar Flask Secret Key" para nova chave

**❓ Dados diferentes entre ambientes:**
- DEV e PROD têm bancos e credenciais separados
- Use o botão DEV/PROD na navbar para alternar

**❓ Como resetar dados:**
- DEV: Remove `data/finance_app_dev.db` e `data/app_settings_dev.json`
- PROD: Remove `data/finance_app_prod.db` e `data/app_settings_prod.json`
---
