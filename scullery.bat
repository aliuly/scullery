@echo off
setlocal
set PYTHONPATH=%PYTHONPATH%;%~dp0;%~dp0\..\ypplib
call %~dp0\pys.bat -m scullery %*

