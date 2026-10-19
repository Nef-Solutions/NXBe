# Overol - demo en modo LOCAL (SQLite, sin backend).
# Uso, desde la raíz del front:  powershell -ExecutionPolicy Bypass -File scripts\demo_local.ps1
#
# Variable de entorno opcional:
#   OVEROL_FRONT_PYTHON  ruta al python.exe del front (por defecto, "python" del PATH)

# "Continue": en PowerShell 5.1, "Stop" convierte el stderr de python en errores;
# cada paso revisa el resultado y falla con su propio mensaje.
$ErrorActionPreference = "Continue"

$Root     = Split-Path -Parent $PSScriptRoot
$FrontPy  = if ($env:OVEROL_FRONT_PYTHON) { $env:OVEROL_FRONT_PYTHON } else { "python" }
$Port     = 8501

function Step($text) { Write-Host "`n==> $text" -ForegroundColor Cyan }
function Fail($text) { Write-Host "`nERROR: $text" -ForegroundColor Red; exit 1 }

Step "Comprobando el Python del front"
if (-not (Get-Command $FrontPy -ErrorAction SilentlyContinue)) { Fail "No se encontró '$FrontPy'. Instala Python o define OVEROL_FRONT_PYTHON con la ruta a python.exe." }
& $FrontPy -c "import streamlit, requests" 2>$null
if ($LASTEXITCODE -ne 0) { Fail "Ese Python no tiene streamlit o requests. Ejecuta: & `"$FrontPy`" -m pip install -r `"$Root\requirements.txt`"" }
Write-Host "    OK: $FrontPy"

Step "Comprobando que el puerto $Port esté libre"
$busy = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($busy) {
    $pid0 = ($busy | Select-Object -First 1).OwningProcess
    Fail "El puerto $Port ya está en uso (proceso $pid0). Cierra la otra instancia de Streamlit y vuelve a intentarlo."
}
Write-Host "    OK: puerto libre"

Step "Arrancando el front en modo local (Ctrl+C para detenerlo)"
$env:OVEROL_BACKEND = "local"
# app.py relanza Streamlit si esta variable no vale "1"; así se evita una instancia duplicada
$env:OVEROL_STREAMLIT_STARTED = "1"
Set-Location $Root
& $FrontPy -m streamlit run app.py --server.port $Port
