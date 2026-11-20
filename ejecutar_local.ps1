# Ejecuta el buscador en este PC y publica los avisos como issues en GitHub.
# Hace lo mismo que .github/workflows/buscar.yml, pero desde tu conexion,
# porque Workday bloquea (error 429) las peticiones que salen de GitHub.
#
# Uso manual:   powershell -ExecutionPolicy Bypass -File .\ejecutar_local.ps1
# Programado:   ver instalar_tarea.ps1
#
# Orden de seguridad: primero se crean los avisos y SOLO despues se guarda
# ofertas_vistas.csv. Si algo falla, el CSV se deja como estaba y la proxima
# ejecucion vuelve a avisar de esas ofertas (mejor repetido que perdido).

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# --- Registro de cada ejecucion en logs\ (no se sube al repositorio) ---------
New-Item -ItemType Directory -Force "logs" | Out-Null
$hoy = Get-Date -Format "yyyy-MM-dd"
Start-Transcript -Path "logs\ejecucion_$hoy.log" -Append | Out-Null

function Buscar-Programa($nombre, $rutaPorDefecto) {
    $cmd = Get-Command $nombre -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    if (Test-Path $rutaPorDefecto) { return $rutaPorDefecto }
    throw "No se encuentra $nombre. Instalalo o revisa la ruta en ejecutar_local.ps1."
}

function Ejecutar($programa, [string[]]$argumentos) {
    & $programa @argumentos
    if ($LASTEXITCODE -ne 0) { throw "Fallo: $programa $($argumentos -join ' ') (codigo $LASTEXITCODE)" }
}

# Textos con tildes y emojis construidos por codigo, para que el archivo sea
# ASCII puro y Windows PowerShell 5.1 lo lea bien sin importar la codificacion.
$enie       = [char]0x00F1
$guion      = [char]0x2013
$espana     = "Espa${enie}a"
$banderaEs  = [char]::ConvertFromUtf32(0x1F1EA) + [char]::ConvertFromUtf32(0x1F1F8)
$mundo      = [char]::ConvertFromUtf32(0x1F30D)
$fecha      = Get-Date -Format "dd/MM/yyyy"

$codigoSalida = 0
try {
    $git = Buscar-Programa "git" "C:\Program Files\Git\cmd\git.exe"
    $gh  = Buscar-Programa "gh"  "C:\Program Files\GitHub CLI\gh.exe"

    # 1. Traer la ultima version (config.yaml y CSV) sin perder cambios locales
    Ejecutar $git @("pull", "--rebase", "--autostash")

    # 2. Preparar Python la primera vez
    $python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path $python)) {
        $pyBase = Buscar-Programa "python" "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
        Ejecutar $pyBase @("-m", "venv", ".venv")
    }
    Ejecutar $python @("-m", "pip", "install", "-q", "-r", "requirements.txt")

    # 3. Buscar ofertas (genera nuevas_*.md y actualiza ofertas_vistas.csv)
    $env:PYTHONUTF8 = "1"
    $env:PYTHONIOENCODING = "utf-8"
    Ejecutar $python @("buscar_ofertas.py")

    # 4. Crear los avisos ANTES de guardar el CSV
    $hayEspana = Test-Path "nuevas_espana.md"
    $hayIntl   = Test-Path "nuevas_internacional.md"
    if ($hayEspana -or $hayIntl) {
        Ejecutar $gh @("label", "create", $espana, "--color", "C60B1E",
                       "--description", "Ofertas ubicadas en $espana", "--force")
        Ejecutar $gh @("label", "create", "Internacional", "--color", "1D76DB",
                       "--description", "Ofertas fuera de $espana", "--force")
    }
    if ($hayEspana) {
        Ejecutar $gh @("issue", "create", "--title", "$banderaEs Ofertas en $espana $guion $fecha",
                       "--label", $espana, "--body-file", "nuevas_espana.md")
    }
    if ($hayIntl) {
        Ejecutar $gh @("issue", "create", "--title", "$mundo Ofertas en otros pa$([char]0x00ED)ses $guion $fecha",
                       "--label", "Internacional", "--body-file", "nuevas_internacional.md")
    }

    # 5. Guardar la lista de ofertas vistas
    Ejecutar $git @("add", "ofertas_vistas.csv")
    & $git diff --cached --quiet
    if ($LASTEXITCODE -eq 0) {
        Write-Output "No hay cambios en ofertas_vistas.csv"
    } else {
        Ejecutar $git @("commit", "-m", "Ofertas actualizadas $hoy (PC local)")
        $subido = $false
        foreach ($intento in 1..3) {
            & $git pull --rebase --autostash
            if ($LASTEXITCODE -eq 0) { & $git push }
            if ($LASTEXITCODE -eq 0) { $subido = $true; break }
            Write-Output "El push ha fallado (intento $intento); reintentando en 10 s"
            Start-Sleep -Seconds 10
        }
        if (-not $subido) { throw "No se pudo subir ofertas_vistas.csv (queda en un commit local; se subira la proxima vez)" }
    }
    Write-Output "Ejecucion completada."
}
catch {
    Write-Output "ERROR: $_"
    $codigoSalida = 1
    # Si no se llego a hacer commit, se descartan los cambios del CSV para que
    # las ofertas no queden marcadas como vistas sin haber avisado de ellas.
    if ($git) {
        try { & $git restore --staged ofertas_vistas.csv } catch {}
        try { & $git restore ofertas_vistas.csv } catch {}
    }
}
finally {
    Remove-Item "nuevas_espana.md", "nuevas_internacional.md" -ErrorAction SilentlyContinue
    Stop-Transcript | Out-Null
}
exit $codigoSalida
