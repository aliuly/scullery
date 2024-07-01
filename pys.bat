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
call %~dp0%WPYDIR%\scripts\env.bat

python %*
