@echo off

:: Script para instalar automaticamente as dependências necessárias

echo Verificando instalacao de dependencias Python...

:: Atualiza o pip
python -m pip install --upgrade pip

:: Instala bibliotecas necessarias
python -m pip install pdfplumber
python -m pip install pandas
python -m pip install openpyxl
python -m pip install xlsxwriter

:: Mensagem final
echo.
echo Todas as dependencias foram instaladas ou ja estavam presentes.
echo Agora voce pode executar o script Python normalmente!
pause
