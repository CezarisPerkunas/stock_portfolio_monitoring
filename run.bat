@echo off
setlocal EnableDelayedExpansion

REM Stock Monitoring App launcher (Windows)
REM
REM Resolves a Python environment in this order:
REM   1) Existing local .venv (if already created)
REM   2) Existing conda env named "stockmon" (under Miniforge/Anaconda)
REM   3) Create .venv from `python` on PATH, install requirements via pip
REM   4) If pip is unavailable/blocked AND miniforge is present, create the
REM      conda env "stockmon" from conda-forge as a fallback.
REM
REM On any failure the window stays open via `pause`.

set "ROOT=%~dp0"
cd /d "%ROOT%"

set "VENV=%ROOT%.venv"
set "VENVPY=%VENV%\Scripts\python.exe"

set "MINIFORGE=C:\Miniforge3"
set "CONDA_ENV_NAME=stockmon"
set "CONDA_ENV_DIR=%MINIFORGE%\envs\%CONDA_ENV_NAME%"
set "CONDA_ENV_PY=%CONDA_ENV_DIR%\python.exe"

set "PY="

REM ---- 1) reuse local venv ----
if exist "%VENVPY%" (
    set "PY=%VENVPY%"
    goto :launch
)

REM ---- 2) reuse existing conda env ----
if exist "%CONDA_ENV_PY%" (
    set "PY=%CONDA_ENV_PY%"
    goto :launch
)

REM ---- 3) create venv with normal python on PATH ----
where python >nul 2>nul
if %errorlevel%==0 (
    echo [run.bat] Creating virtual environment at "%VENV%" ...
    python -m venv "%VENV%"
    if errorlevel 1 (
        echo [run.bat] WARN: 'python -m venv' failed.
        goto :try_conda
    )

    echo [run.bat] Installing requirements via pip ...
    "%VENVPY%" -m pip install --disable-pip-version-check --upgrade pip
    if errorlevel 1 (
        echo [run.bat] WARN: pip upgrade failed ^(pip may be blocked by policy^).
        goto :try_conda
    )
    "%VENVPY%" -m pip install --disable-pip-version-check -r "%ROOT%requirements.txt"
    if errorlevel 1 (
        echo [run.bat] WARN: pip install failed ^(packages may be blocked^).
        goto :try_conda
    )

    set "PY=%VENVPY%"
    goto :launch
)

:try_conda
REM ---- 4) fallback: build conda env from miniforge ----
if not exist "%MINIFORGE%\python.exe" (
    echo [run.bat] ERROR: No working Python found.
    echo            Install Python from https://www.python.org/downloads/
    echo            OR install Miniforge at "%MINIFORGE%".
    pause
    exit /b 1
)

set "MAMBA=%MINIFORGE%\condabin\mamba.bat"
set "CONDA=%MINIFORGE%\condabin\conda.bat"
set "INSTALLER=%MAMBA%"
if not exist "%INSTALLER%" set "INSTALLER=%CONDA%"

echo [run.bat] Falling back to conda. Creating env "%CONDA_ENV_NAME%" ...
echo            This will take a few minutes on first run.
call "%INSTALLER%" create -y -n %CONDA_ENV_NAME% -c conda-forge ^
    python=3.12 ^
    streamlit ^
    yfinance ^
    pandas ^
    numpy ^
    scipy ^
    plotly ^
    statsmodels ^
    pyportfolioopt ^
    pandas-datareader ^
    python-dateutil
if errorlevel 1 (
    echo [run.bat] ERROR: conda env creation failed.
    pause
    exit /b 1
)
if not exist "%CONDA_ENV_PY%" (
    echo [run.bat] ERROR: conda env python not found at "%CONDA_ENV_PY%".
    pause
    exit /b 1
)
set "PY=%CONDA_ENV_PY%"

:launch
echo [run.bat] Using Python: %PY%
echo [run.bat] Launching Streamlit ...
"%PY%" -m streamlit run "%ROOT%app.py"
if errorlevel 1 (
    echo [run.bat] Streamlit exited with an error.
    pause
)

endlocal
