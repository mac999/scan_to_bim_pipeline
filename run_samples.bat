@echo off
rem runs the sample pipelines. build the C++ stages first with build.bat
rem usage: run_samples.bat [all^|indoor^|pipe]
rem   indoor  conference_room1, rule-based walls and slabs. needs the C++ stages
rem   pipe    kict_mep_zero_en_bdlg_parts, pipes and elbows
rem env: PYTHON (default python)

setlocal
cd /d "%~dp0"
if "%PYTHON%"=="" set PYTHON=python
set TARGET=%~1
if "%TARGET%"=="" set TARGET=all
if "%TARGET%"=="all" goto start
if "%TARGET%"=="indoor" goto start
if "%TARGET%"=="pipe" goto start
echo usage: run_samples.bat [all^|indoor^|pipe]
exit /b 1

:start
set FAILED=0
if "%TARGET%"=="pipe" goto pipe
if exist bin\pcd_to_seg.exe if exist bin\seg_to_geo.exe goto indoor
echo indoor: skipped, run build.bat first
set FAILED=1
goto indoor_done
:indoor
call :sample indoor "./input/conference_room1/*.pcd" indoor_rule output\conference_room1\geo_to_bim_indoor\geo_to_bim_indoor.ifc
:indoor_done
if "%TARGET%"=="indoor" goto end
:pipe
call :sample pipe "./input/kict_mep_zero_en_bdlg_parts/*.laz" pipe_rule output\kict_mep_zero_en_bdlg_parts\geo_to_bim_pipe\geo_to_bim_pipe.ifc
:end
exit /b %FAILED%

:sample
rem name, input glob, pipeline, result file
echo == %~1: %~3
if exist "%~4" del "%~4"
%PYTHON% pipeline\app.py --input_path "%~2" --stage %~3
if exist "%~4" (
    echo %~1: %~4
) else (
    echo %~1: failed, no %~4
    set FAILED=1
)
exit /b 0
