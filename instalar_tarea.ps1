# Registra (o actualiza) la tarea del Programador de tareas de Windows que
# ejecuta ejecutar_local.ps1 todos los dias a las horas indicadas.
#
# Uso:  powershell -ExecutionPolicy Bypass -File .\instalar_tarea.ps1
#       powershell -ExecutionPolicy Bypass -File .\instalar_tarea.ps1 -Horas "08:30","14:00","20:00"
# Para quitarla:  Unregister-ScheduledTask -TaskName "Buscador de practicas" -Confirm:$false
#
# La tarea se ejecuta con tu usuario y solo cuando has iniciado sesion (no
# guarda ninguna contrasena). Si el PC estaba apagado a la hora prevista, se
# ejecuta en cuanto lo enciendas.

param(
    [string[]]$Horas = @("09:00", "18:00"),
    [string]$Nombre = "Buscador de practicas"
)

$ErrorActionPreference = "Stop"
$script = Join-Path $PSScriptRoot "ejecutar_local.ps1"

$accion = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`"" `
    -WorkingDirectory $PSScriptRoot

$disparadores = foreach ($h in $Horas) { New-ScheduledTaskTrigger -Daily -At $h }

$ajustes = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -MultipleInstances IgnoreNew

$usuario = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $Nombre -Action $accion -Trigger $disparadores `
    -Settings $ajustes -Principal $usuario `
    -Description "Busca ofertas de practicas en Workday y crea issues en GitHub (buscador-practicas)" `
    -Force | Out-Null

Write-Output "Tarea '$Nombre' registrada: todos los dias a las $($Horas -join ', ')."
Write-Output "Registro de cada ejecucion: $(Join-Path $PSScriptRoot 'logs')"
