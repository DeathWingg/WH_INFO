@echo off
title WH INFO - Compilador
echo Preparando o aplicativo para Windows...

call .venv\Scripts\activate
if errorlevel 1 (
  echo [ERRO] Ative o ambiente virtual antes.
  pause
  exit /b 1
)

echo.
echo Gerando executavel (isso pode demorar alguns minutos)...
pyinstaller --noconfirm --clean --windowed --onedir --name WH_INFO ^
  --add-data "templates;templates" ^
  --add-data "static;static" ^
  --add-data "services;services" ^
  --hidden-import services.pricing ^
  --hidden-import services.pdf_generator ^
  --hidden-import services.backup ^
  --hidden-import services.product_search ^
  --collect-all reportlab ^
  --collect-all PIL ^
  --collect-all duckduckgo_search ^
  run.py

echo.
echo Processo concluido! O aplicativo esta na pasta: dist\WH_INFO\WH_INFO.exe
pause