@echo off
setlocal EnableDelayedExpansion

echo ==========================================
echo      Pillow-SIMD Builder for Windows
echo ==========================================

REM --- CONFIGURATION ---
REM 1. Visual Studio Path
set "VS_PATH=C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"

REM 2. VCPKG Path (Defaults to Scoop location)
set "VCPKG_BASE=%USERPROFILE%\scoop\apps\vcpkg\current\installed\x64-windows"

REM --- CHECKS ---
if not exist "%VS_PATH%" (
    echo [ERROR] Could not find Visual Studio 2022.
    echo Path checked: "%VS_PATH%"
    pause
    exit /b 1
)

if not exist "%VCPKG_BASE%" (
    echo [ERROR] Could not find vcpkg libraries.
    echo Path checked: "%VCPKG_BASE%"
    echo.
    echo Did you run: vcpkg install zlib libjpeg-turbo --triplet=x64-windows ?
    pause
    exit /b 1
)

REM --- STEP 1: Choose Tooling ---
echo.
echo Do you want to use 'uv' to install build dependencies?
echo [Y] Yes - Faster (Requires uv installed)
echo [N] No  - Use standard pip
set /p USE_UV="Selection (Y/N): "

if /i "!USE_UV!"=="Y" (
    echo [Config] Mode: UV
    set "PREP_CMD=uv pip install"
) else (
    echo [Config] Mode: Standard Pip
    set "PREP_CMD=python -m pip install"
)

REM --- STEP 2: Load VS Environment ---
echo.
echo [1/6] Loading Visual Studio Environment...
call "%VS_PATH%" >nul
if %errorlevel% neq 0 (
    echo [ERROR] Failed to load vcvars64.bat
    pause
    exit /b 1
)

REM --- STEP 3: Set Compiler Flags ---
echo [2/6] Configuring Compiler Paths...
set "INCLUDE=%INCLUDE%;%VCPKG_BASE%\include"
set "LIB=%LIB%;%VCPKG_BASE%\lib"
set "ZLIB_ROOT=%VCPKG_BASE%"
set "JPEG_ROOT=%VCPKG_BASE%"

REM --- STEP 4: Install Dependencies ---
echo [3/6] Installing build tools...
REM Installing wheel and delvewheel so we can build and repair the package
%PREP_CMD% wheel delvewheel
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

REM --- STEP 5: Compile ---
echo [4/6] Compiling Pillow-SIMD wheel...
echo (This downloads source from PyPI and compiles it locally)

REM Clean up any existing wheels in root to avoid confusion
if exist "pillow_simd*.whl" del /q "pillow_simd*.whl"
if exist "Pillow_SIMD*.whl" del /q "Pillow_SIMD*.whl"

REM We intentionally use standard 'pip wheel' here. 
REM 'uv build' expects a local source folder, but we want to download from PyPI.
python -m pip wheel pillow-simd --no-binary :all: --no-deps
if %errorlevel% neq 0 (
    echo [ERROR] Compilation failed.
    pause
    exit /b 1
)

REM --- STEP 6: Repair (Bundle DLLs) ---
echo.
echo [5/6] Bundling DLLs...
if exist wheelhouse rmdir /s /q wheelhouse

REM Run delvewheel to bake the vcpkg DLLs into the wheel
delvewheel repair --add-path "%VCPKG_BASE%\bin" pillow_simd-*.whl

REM --- STEP 7: Cleanup ---
echo [6/6] Cleaning up temporary files...

REM Deleting the "unrepaired" wheel so only the correct one remains
if exist "pillow_simd*.whl" del /q "pillow_simd*.whl"
if exist "Pillow_SIMD*.whl" del /q "Pillow_SIMD*.whl"

echo.
echo ==========================================
echo SUCCESS! 
echo.
echo The standalone wheel is located in the "wheelhouse" folder.
echo You can share this file with others.
echo.
echo ==========================================
pause
