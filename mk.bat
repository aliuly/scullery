@echo off
setlocal
rd/s/q %~dp0%build
rd/s/q %~dp0%dist
del *.spec
set build=%~dp0%scripts\build.bat

set VENV=%~dp0.venv
call %VENV%\Scripts\activate.bat

set src=scullery

call %build% -1 %src%\__main__.py --name %src% -p %src% -p .

dir dist
dist\%src% -h

