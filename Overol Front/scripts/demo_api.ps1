# Overol - demo en modo API (front conectado al backend Django).
# Uso, desde la raíz del front:  powershell -ExecutionPolicy Bypass -File scripts\demo_api.ps1
#
# Variables de entorno opcionales:
#   OVEROL_FRONT_PYTHON    ruta al python.exe del front (por defecto, "python" del PATH)
#   OVEROL_BACKEND_PYTHON  Python 3.12+ para crear el entorno del backend (por defecto, "py -3.12")
#   OVEROL_BACKEND_DIR     carpeta del backend Django (por defecto, .\backend junto a app.py
#                          o, si no existe, ..\backend como en el repositorio del equipo)
#   OVEROL_BACKEND_VENV    entorno virtual del backend (por defecto, %LOCALAPPDATA%\Overol\backend_venv)
#
# No escribe nada dentro de la carpeta del backend: el entorno vive fuera y se usa PYTHONDONTWRITEBYTECODE=1.

# "Continue": en PowerShell 5.1, "Stop" convierte el stderr de docker/python en errores;
# cada paso revisa $LASTEXITCODE y falla con su propio mensaje.
$ErrorActionPreference = "Continue"

$Root       = Split-Path -Parent $PSScriptRoot
$Backend    = if ($env:OVEROL_BACKEND_DIR) { $env:OVEROL_BACKEND_DIR } else { Join-Path $Root "backend" }
# En el repositorio, backend/ está al lado de la carpeta del front y no dentro
if (-not $env:OVEROL_BACKEND_DIR -and -not (Test-Path -LiteralPath (Join-Path $Backend "manage.py"))) {
    $Backend = Join-Path (Split-Path -Parent $Root) "backend"
}
if (Test-Path -LiteralPath $Backend) { $Backend = (Resolve-Path -LiteralPath $Backend).Path }
$FrontPy    = if ($env:OVEROL_FRONT_PYTHON) { $env:OVEROL_FRONT_PYTHON } else { "python" }
$Venv       = if ($env:OVEROL_BACKEND_VENV) { $env:OVEROL_BACKEND_VENV } else { Join-Path $env:LOCALAPPDATA "Overol\backend_venv" }
$VenvPy     = Join-Path $Venv "Scripts\python.exe"
$ApiUrl     = "http://127.0.0.1:8000/api/"
$FrontPort  = 8501
$WaitSecs   = 60

function Step($text) { Write-Host "`n==> $text" -ForegroundColor Cyan }
function Ok($text)   { Write-Host "    OK: $text" -ForegroundColor Green }
function Fail($text) { Write-Host "`nERROR: $text" -ForegroundColor Red; exit 1 }

# Devuelve $true si el servidor contesta cualquier código HTTP (incluido 404)
function Test-Api {
    try {
        Invoke-WebRequest -UseBasicParsing -Uri $ApiUrl -TimeoutSec 3 | Out-Null
        return $true
    } catch [System.Net.WebException] {
        return ($null -ne $_.Exception.Response)
    } catch {
        return $false
    }
}

# Python 3.12+ para crear el entorno del backend: OVEROL_BACKEND_PYTHON o "py -3.12"
function Get-BackendPython {
    if ($env:OVEROL_BACKEND_PYTHON) { return $env:OVEROL_BACKEND_PYTHON }
    if (-not (Get-Command py -ErrorAction SilentlyContinue)) { return $null }
    $exe = & py -3.12 -c "import sys; print(sys.executable)" 2>$null
    if ($LASTEXITCODE -eq 0 -and $exe) { return "$exe".Trim() }
    return $null
}

$env:PYTHONDONTWRITEBYTECODE = "1"

# ------------------------------------------------------------------
Step "Comprobando el Python del front, la carpeta del backend y el puerto $FrontPort"
if (-not (Get-Command $FrontPy -ErrorAction SilentlyContinue)) { Fail "No se encontró '$FrontPy'. Instala Python o define OVEROL_FRONT_PYTHON con la ruta a python.exe." }
if (-not (Test-Path -LiteralPath (Join-Path $Backend "manage.py"))) { Fail "No se encontró el backend en `"$Backend`" (falta manage.py). Define OVEROL_BACKEND_DIR con la carpeta del backend Django." }
Ok "Backend encontrado en `"$Backend`""
& $FrontPy -c "import streamlit, requests" 2>$null
if ($LASTEXITCODE -ne 0) { Fail "El Python del front no tiene streamlit o requests. Ejecuta: & `"$FrontPy`" -m pip install -r `"$Root\requirements.txt`"" }
if (Get-NetTCPConnection -LocalPort $FrontPort -State Listen -ErrorAction SilentlyContinue) {
    Fail "El puerto $FrontPort ya está en uso. Cierra la otra instancia de Streamlit y vuelve a intentarlo."
}
Ok "Python del front listo y puerto libre"

# ------------------------------------------------------------------
Step "(a) Comprobando Docker y levantando Postgres y Redis"
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { Fail "Docker no está instalado o no está en el PATH." }
docker info --format "{{.ServerVersion}}" *> $null
if ($LASTEXITCODE -ne 0) { Fail "Docker no está corriendo. Abre Docker Desktop, espera a que diga 'Running' y vuelve a ejecutar este script." }
Ok "Docker está corriendo"

# docker-compose.yml del backend toma POSTGRES_* de backend\.env; sin él, Compose correría con valores vacíos
if (-not (Test-Path -LiteralPath (Join-Path $Backend ".env"))) {
    Fail "Falta `"$Backend\.env`". Cópialo desde .env.example (Copy-Item `"$Backend\.env.example`" `"$Backend\.env`") y completa sus valores según la documentación del backend."
}

Push-Location $Backend
try {
    docker compose up -d
    if ($LASTEXITCODE -ne 0) { Fail "docker compose up -d falló en $Backend. Revisa el mensaje de arriba." }
} finally {
    Pop-Location
}

Write-Host "    Esperando a que Postgres acepte conexiones..."
$pgReady = $false
for ($i = 0; $i -lt 30; $i++) {
    docker exec overol_db pg_isready -q *> $null
    if ($LASTEXITCODE -eq 0) { $pgReady = $true; break }
    Start-Sleep -Seconds 1
}
if (-not $pgReady) { Fail "Postgres (contenedor overol_db) no respondió en 30 segundos. Revisa: docker compose logs db" }
Ok "Postgres y Redis arriba"

# ------------------------------------------------------------------
Step "(b) Comprobando el entorno del backend en $Venv"
if (-not (Test-Path $VenvPy)) {
    $Py312 = Get-BackendPython
    if (-not $Py312) { Fail "No existe el entorno y no se encontró Python 3.12 ('py -3.12'). Django 6.1 exige 3.12+: instálalo o define OVEROL_BACKEND_PYTHON." }
    Write-Host "    No existe: creándolo con Python 3.12 (puede tardar un par de minutos)..."
    New-Item -ItemType Directory -Force (Split-Path -Parent $Venv) | Out-Null
    & $Py312 -m venv $Venv
    if ($LASTEXITCODE -ne 0) { Fail "No se pudo crear el entorno en $Venv." }
    & $VenvPy -m pip install --disable-pip-version-check -q -r (Join-Path $Backend "documentacion\requirements.txt")
    if ($LASTEXITCODE -ne 0) { Fail "Falló la instalación de backend\documentacion\requirements.txt." }
}
& $VenvPy -c "import django" 2>$null
if ($LASTEXITCODE -ne 0) { Fail "El entorno $Venv existe pero no tiene Django. Bórralo y vuelve a ejecutar el script para recrearlo." }
Ok "Entorno listo ($(& $VenvPy -c "import sys, django; print(sys.version.split()[0], '- Django', django.get_version())"))"

# ------------------------------------------------------------------
Step "(c) Aplicando migraciones y levantando el backend"
if (Test-Api) {
    Ok "Ya hay un servidor respondiendo en $ApiUrl; no se levanta otro"
} else {
    Push-Location $Backend
    try {
        & $VenvPy manage.py migrate --noinput
        if ($LASTEXITCODE -ne 0) { Fail "manage.py migrate falló. Revisa el mensaje de arriba." }
    } finally {
        Pop-Location
    }

    $serverCmd = "`$env:PYTHONDONTWRITEBYTECODE='1'; `$Host.UI.RawUI.WindowTitle='Overol backend (runserver)'; " +
                 "Set-Location '$Backend'; & '$VenvPy' manage.py runserver 127.0.0.1:8000"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $serverCmd | Out-Null
    Ok "runserver iniciado en una ventana aparte (ciérrala para detener el backend)"
}

# ------------------------------------------------------------------
Step "(d) Esperando a que $ApiUrl responda (máximo $WaitSecs s)"
$up = $false
for ($i = 0; $i -lt $WaitSecs; $i++) {
    if (Test-Api) { $up = $true; break }
    Start-Sleep -Seconds 1
}
if (-not $up) { Fail "El backend no respondió en $WaitSecs segundos. Revisa la ventana 'Overol backend (runserver)'." }
Ok "Backend respondiendo"

# ------------------------------------------------------------------
Step "(e) Arrancando el front en modo api (Ctrl+C para detenerlo)"
$env:OVEROL_BACKEND = "api"
$env:OVEROL_API_URL = $ApiUrl
# app.py relanza Streamlit si esta variable no vale "1"; así se evita una instancia duplicada
$env:OVEROL_STREAMLIT_STARTED = "1"
Set-Location $Root
& $FrontPy -m streamlit run app.py --server.port $FrontPort
