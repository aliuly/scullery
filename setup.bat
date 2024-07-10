REM ~ @echo off
setlocal

if EXIST %~dp0%env.bat (
  call %~dp0%env.bat 
)
if EXIST %~dp0%..\env.bat (
  call %~dp0%..\env.bat
)
if NOT "%proxy%"=="" (
  set http_proxy=http://%proxy%/
  set https_proxy=http://%proxy%/
  set pipproxy=--proxy=%proxy%
) else (
  set pipproxy=
)

set VENV=%~dp0.venv
if NOT EXIST %VENV%\Scripts\activate.bat (
  if "%1"=="exe" (
    echo Setting VENV-exe
    python.exe -m venv --system-site-packages %VENV%
  ) else (
    echo Setting VENV-bat
    call python.bat -m venv --system-site-packages %VENV%
  )
)
call %VENV%\Scripts\activate.bat

pip install %pipproxy% --requirement %~dp0%requirements.txt

if "%1"=="exe" (
  pip install %pipproxy% pyinstaller
) else (
  pip install %pipproxy% icecream
  pip install %pipproxy% pyinstaller
)
