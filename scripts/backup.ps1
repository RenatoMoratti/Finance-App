param(
  [string]$EnvName = "development",
  [string]$PythonPath = "python"
)

$ErrorActionPreference = 'Stop'

function Timestamp { (Get-Date).ToString('yyyy-MM-dd HH:mm:ss') }

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppRoot = Split-Path -Parent $ScriptRoot
Set-Location $AppRoot

Write-Host "[$(Timestamp)] Iniciando backup (env=$EnvName)" -ForegroundColor Cyan

$Code = @'
import sys, os, traceback
from datetime import datetime

APP_ROOT = r"{APP_ROOT}"
if APP_ROOT and APP_ROOT not in sys.path:
  sys.path.insert(0, APP_ROOT)

def now():
  return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

try:
  from backup_manager import perform_backup
  from config import Config
  from environment_manager import environment_manager
except Exception as e:
  print(f"[{now()}] Falha ao importar módulos: {e}\n{traceback.format_exc()}")
  import sys as _sys
  _sys.exit(2)

try:
  env_file_env = environment_manager.get_current_environment()
  if env_file_env not in ("production", "development"):
    env_file_env = "development"
  target_env = "{ENV_PLACEHOLDER}" or env_file_env
  db_path = Config.get_database_path()
  print(f"[{now()}] Iniciando backup Python (env_resolvido={target_env}, db={db_path})")
  created, detail = perform_backup(db_path, target_env, force=False, max_hours=24)
  print(f"[{now()}] Resultado: criado={created} detalhe={detail}")
except Exception as e:
  print(f"[{now()}] Erro durante execução do backup: {e}\n{traceback.format_exc()}")
  import sys as _sys
  _sys.exit(3)
'@

$Code = $Code.Replace('{ENV_PLACEHOLDER}', $EnvName)
$Code = $Code.Replace('{APP_ROOT}', $AppRoot)

$tempFile = New-TemporaryFile
Set-Content -Path $tempFile -Value $Code -Encoding UTF8

Write-Host "[$(Timestamp)] Executando Python: $PythonPath" -ForegroundColor Yellow
& $PythonPath $tempFile
$exitCode = $LASTEXITCODE
Remove-Item $tempFile -Force

if ($exitCode -ne 0) {
  Write-Host "[$(Timestamp)] Backup terminou com erros (exit=$exitCode)" -ForegroundColor Red
  exit $exitCode
}

Write-Host "[$(Timestamp)] Backup concluído com sucesso" -ForegroundColor Green
