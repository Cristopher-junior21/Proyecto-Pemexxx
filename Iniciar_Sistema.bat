@echo off
setlocal
cd /d "%~dp0"
title Sistema de Capacitacion Cangrejera

if not exist ".venv\Scripts\python.exe" (
    echo Preparando el entorno virtual por primera vez...
    where py >nul 2>&1
    if errorlevel 1 (
        echo ERROR: No se encontro Python Launcher (py).
        echo Instala Python para Windows y prueba nuevamente.
        pause
        exit /b 1
    )
    py -m venv .venv
    if errorlevel 1 (
        echo ERROR: No se pudo crear el entorno virtual.
        pause
        exit /b 1
    )
)

".venv\Scripts\python.exe" -c "import PySide6, mysql.connector, dotenv, argon2, reportlab" >nul 2>&1
if errorlevel 1 (
    echo Instalando dependencias necesarias (solo la primera vez)...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: No se pudieron instalar las dependencias.
        pause
        exit /b 1
    )
)

if exist "logica\autenticacion.py" (
    ".venv\Scripts\python.exe" -c "import argon2" >nul 2>&1
    if errorlevel 1 (
        echo Instalando seguridad de inicio de sesion...
        ".venv\Scripts\python.exe" -m pip install argon2-cffi
        if errorlevel 1 (
            echo ERROR: No se pudo instalar argon2-cffi.
            pause
            exit /b 1
        )
    )
)

if not exist ".env" (
    echo AVISO: No se encontro el archivo .env con la configuracion de MySQL.
    echo Crea .env a partir de .env.example y configura tu acceso local.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" main.py
if errorlevel 1 (
    echo.
    echo El sistema termino con un error. Lee el mensaje de arriba.
    pause
    exit /b 1
)
endlocal
