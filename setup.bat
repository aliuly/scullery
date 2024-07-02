REM ~ @echo off
setlocal

if EXIST %~dp0%env.bat (
  call %~dp0%env.bat 
)
if EXIST %~dp0%..\env.bat (
  call %~dp0%..\env.bat
)
if NOT "%proxy"=="" (
  set http_proxy=http://%proxy%/
  set https_proxy=http://%proxy%/
  set pipproxy=--proxy=%proxy%
) else (
  set pipproxy=
)

call %~dp0%windows\pyver.bat

if NOT EXIST %~dp0%WPYDIR%\scripts\env.bat (
  %~dp0\windows\wget.exe -S https://github.com/winpython/winpython/releases/download/%WPYREL%/%WPYDIST%
  %WPYDIST% -o"%~dp0" -y
)
call %~dp0%WPYDIR%\scripts\env.bat
pip install %pipproxy% --requirement %~dp0%requirements.txt
pip install %pipproxy% icecream
REM ~ pip install %pipproxy% pyinstaller
