@echo off
setlocal
call %~dp0%..\vars.bat

python %~dp0\findsitepkgs.py > %~dp0\sitedir.bat
call %~dp0\sitedir.bat
echo SITEDIR:%sitedir%
del %~dp0\sitedir.bat
REM ~ set sitedir=%WINPYDIR%\Lib\site-packages
set buildtype=--onefile

rem
rem Usage:
rem build.bat (opts)
rem 
rem Options:
rem
rem * -1 : generate a single EXE file
rem * -d : generage a single DIR
rem * --openstack : OpenStack predefines

set script=
set line=
set BUILD_OPTS=
:loop
REM this loop does NOT handle double quotes "
if NOT "%1" =="" (
  IF "%1"=="-1" (
    SET buildtype=--onefile
    SHIFT
    goto :loop
  )
  IF "%1"=="-d" (
    SET buildtype=--onedir
    SHIFT
    goto :loop
  )
  if "%script%"=="" (
    set script=%1
  ) else (
    set line=%line% %1
  )
  SHIFT
  goto :loop
)

echo BUILD:%buildtype%
echo OPTS:%BUILD_OPTS%
echo SCRIPT:%script%
echo ARGS:%line%

pyinstaller %buildtype% %BUILD_OPTS% %script% %line%


:DONE
