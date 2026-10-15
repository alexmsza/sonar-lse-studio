@echo off
chcp 65001 >nul
title SONAR LSE Studio - Servidor Local

echo =====================================================================
echo                  SONAR — LSE STUDIO (ANIMAGE FESTIVAL)
echo          Legendagem Descritiva de Foley, Sonoplastia e Ruídos
echo =====================================================================
echo.

cd /d "%~dp0"

echo [1/3] Verificando dependências com UV...
where uv >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] UV detectado no sistema.
    echo [2/3] Sincronizando ambiente...
    call uv sync >nul 2>&1
    echo [3/3] Iniciando servidor e abrindo estúdio no navegador...
    start "" http://127.0.0.1:8000
    call uv run python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
) else (
    echo [AVISO] UV não encontrado no PATH direto. Tentando Python nativo...
    where python >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        python -m pip install -q -r requirements.txt >nul 2>&1
        start "" http://127.0.0.1:8000
        python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
    ) else (
        echo [ERRO] Python ou UV não foram encontrados. Por favor instale o Python ou UV.
        pause
    )
)
