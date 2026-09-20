@echo off
setlocal
set "QWEN35_APP_ROOT=%~dp0"
powershell -NoProfile -Command "$ErrorActionPreference='Stop'; $root=$env:QWEN35_APP_ROOT; $py=Join-Path $root '.venv\Scripts\python.exe'; $config=Join-Path $root 'config-local.json'; if(Test-Path -LiteralPath $config){$c=Get-Content -LiteralPath $config -Raw -Encoding UTF8 | ConvertFrom-Json; if($c.python_executable){$py=[string]$c.python_executable}; if($c.python_site_packages){$env:PYTHONPATH=[string]$c.python_site_packages}}; if(-not (Test-Path -LiteralPath $py)){throw 'Python local indisponivel. Consulte README.md.'}; & $py (Join-Path $root 'launcher.py'); exit $LASTEXITCODE"
if errorlevel 1 pause
endlocal
