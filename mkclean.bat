@echo off
setlocal
rd/s/q %~dp0%build
rd/s/q %~dp0%dist
del *.spec
