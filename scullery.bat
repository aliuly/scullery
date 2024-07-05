@echo off
setlocal
set PYTHONPATH=%PYTHONPATH%;%~dp0
call %~dp0\pys.bat -m scullery %*

