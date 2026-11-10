@echo off
rem builds the C++ stages into .\bin.
rem usage: build.bat [--install]
rem   --install  pip install requirements_simple.txt first
rem env: PYTHON (default python). PCL is found through CONDA_PREFIX or VCPKG_ROOT when set

setlocal
cd /d "%~dp0"
if "%PYTHON%"=="" set PYTHON=python

if "%~1"=="" goto build
if not "%~1"=="--install" (
    echo usage: build.bat [--install]
    exit /b 1
)
echo == install python packages
%PYTHON% -m pip install -r requirements_simple.txt || exit /b 1

:build
echo == build C++ stages
set OPTIONS=
if not "%CONDA_PREFIX%"=="" set OPTIONS=-DCMAKE_PREFIX_PATH="%CONDA_PREFIX%\Library"
if not "%VCPKG_ROOT%"=="" set OPTIONS=%OPTIONS% -DCMAKE_TOOLCHAIN_FILE="%VCPKG_ROOT%\scripts\buildsystems\vcpkg.cmake"
cmake -S . -B build %OPTIONS%
if errorlevel 1 goto failed
cmake --build build --config Release
if errorlevel 1 goto failed
dir /b bin
exit /b 0
:failed
echo build failed
exit /b 1
