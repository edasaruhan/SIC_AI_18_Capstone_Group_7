@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" goto find_python
".venv\Scripts\python.exe" -c "import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else 1)" >nul 2>&1
if errorlevel 1 goto find_python
".venv\Scripts\python.exe" tools\start_demo.py %*
set "launcher_status=%errorlevel%"
goto finish

:find_python
where py >nul 2>&1
if errorlevel 1 goto try_python
py -3.12 -c "import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else 1)" >nul 2>&1
if errorlevel 1 goto try_python
py -3.12 tools\start_demo.py %*
set "launcher_status=%errorlevel%"
goto finish

:try_python
python -c "import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else 1)" >nul 2>&1
if errorlevel 1 goto missing_python
python tools\start_demo.py %*
set "launcher_status=%errorlevel%"
goto finish

:missing_python
echo Python 3.12 is required. Install it, then run this launcher again.
set "launcher_status=1"

:finish
if not "%launcher_status%"=="0" pause
exit /b %launcher_status%
