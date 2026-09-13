@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto dependencies
py -3.12 -c "import sys; assert sys.version_info[:2] == (3, 12)" >nul 2>&1
if errorlevel 1 goto try_python
py -3.12 -m venv .venv
if errorlevel 1 goto failed
goto dependencies
:try_python
python -c "import sys; assert sys.version_info[:2] == (3, 12)" >nul 2>&1
if errorlevel 1 goto no_python
python -m venv .venv
if errorlevel 1 goto failed
if not exist ".venv\Scripts\python.exe" goto no_python
:dependencies
".venv\Scripts\python.exe" -c "import streamlit, jsonschema, pandas, PIL" >nul 2>&1
if not errorlevel 1 goto run
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
:run
echo Opening Product Label Designer at http://localhost:8501
echo Keep this window open while using the app. Press Ctrl+C to stop.
".venv\Scripts\python.exe" -m streamlit run app.py
if errorlevel 1 goto failed
exit /b 0
:no_python
echo Python 3.12 was not found. Install Python 3.12, select Add python.exe to PATH,
echo close this window and double-click this file again.
pause
exit /b 1
:failed
echo Startup failed. Please copy the error above or take a screenshot.
pause
exit /b 1
