<#
.SYNOPSIS
  Grabador seguro de imágenes USB para LA AGUJA en Windows.
  Valida la identidad tras UAC y verifica todos los bytes grabados.
#>
param(
    [Parameter(Mandatory=$true)][string]$ImagePath,
    [Parameter(Mandatory=$true)][ValidateRange(0,2147483647)][int]$DiskNumber,
    [Parameter(Mandatory=$true)][ValidateNotNullOrEmpty()][string]$ExpectedSerial,
    [Parameter(Mandatory=$true)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$ExpectedSha256,
    [Parameter(Mandatory=$true)][ValidateRange(1,9223372036854775807)][long]$ExpectedSize,
    [Parameter(Mandatory=$true)][ValidateNotNullOrEmpty()][string]$ExpectedModel,
    [int]$SupervisorPID = 0,
    [int]$ApplicationPID = 0
)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$OutputEncoding = [Console]::OutputEncoding
$fileStream = $null
$diskStream = $null
$readStream = $null
$shaAlg = $null
$readShaAlg = $null
$dpFile = $null
$exitCode = 1

function Emit-Json($obj) { Write-Output ($obj | ConvertTo-Json -Compress) }
function Assert-Supervisor {
    foreach ($watchedPID in @($SupervisorPID,$ApplicationPID)) {
        if ($watchedPID -le 0) { continue }
        try { $supervisor = [System.Diagnostics.Process]::GetProcessById($watchedPID) }
        catch { throw 'La aplicación se cerró. La grabación del USB se detuvo.' }
        try {
            if ($supervisor.HasExited) { throw 'La aplicación se cerró. La grabación del USB se detuvo.' }
        } finally { $supervisor.Dispose() }
    }
}
function Assert-Target([long]$ImageBytes) {
    Assert-Supervisor
    $disk = Get-Disk -Number $DiskNumber -ErrorAction Stop
    if ($disk.IsSystem -or $disk.IsBoot) { throw 'Operación denegada: el disco es del sistema o de arranque.' }
    if ($disk.BusType -ne 'USB') { throw 'Operación denegada: el disco no es un dispositivo USB.' }
    if ($disk.IsReadOnly) { throw 'El USB está protegido contra escritura.' }
    $serial = if ($disk.SerialNumber) { $disk.SerialNumber.Trim() } else { "USB-$DiskNumber" }
    $model = if ($disk.FriendlyName) { $disk.FriendlyName.Trim() } else { 'USB Drive' }
    if ($serial -cne $ExpectedSerial -or $disk.Size -ne $ExpectedSize -or $model -cne $ExpectedModel) {
        throw 'La identidad del USB cambió. Vuelve a seleccionarlo antes de grabar.'
    }
    if ($disk.Size -lt $ImageBytes) { throw 'El USB no tiene suficiente capacidad para la imagen.' }
    return $disk
}
try {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Se necesitan permisos de administrador de Windows para grabar el USB.'
    }
    if (-not ('Aguja.WindowsDiskLock' -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;
namespace Aguja {
    public static class WindowsDiskLock {
        [DllImport("kernel32.dll", SetLastError = true)]
        public static extern bool DeviceIoControl(SafeFileHandle handle, uint code,
            IntPtr input, int inputSize, IntPtr output, int outputSize,
            out uint returned, IntPtr overlapped);
    }
}
'@
    }
    # Keep the verified image handle open: no replacement/write/delete may
    # occur between hashing and streaming its bytes to the USB.
    $fileStream = [System.IO.File]::Open($ImagePath,[System.IO.FileMode]::Open,[System.IO.FileAccess]::Read,[System.IO.FileShare]::Read)
    $imageBytes = $fileStream.Length
    if ($imageBytes -le 0) { throw 'La imagen está vacía.' }
    $disk = Assert-Target $imageBytes
    Emit-Json @{type='progress';stage='verify';message='Comprobando imagen original…'}
    $shaAlg = [System.Security.Cryptography.SHA256]::Create()
    $calcSha = [System.BitConverter]::ToString($shaAlg.ComputeHash($fileStream)).Replace('-','').ToLowerInvariant()
    if ($calcSha -ne $ExpectedSha256.ToLowerInvariant()) { throw 'El SHA-256 de la imagen no coincide con el valor esperado.' }
    $fileStream.Position = 0
    # Hashing and UAC may take minutes. Revalidate immediately before cleaning.
    $disk = Assert-Target $imageBytes
    Emit-Json @{type='progress';stage='write';message='Limpiando particiones del USB…'}
    $dpFile = [System.IO.Path]::GetTempFileName()
    [System.IO.File]::WriteAllText($dpFile,"rescan`r`n",[System.Text.Encoding]::ASCII)
    & (Join-Path $env:SystemRoot 'System32\diskpart.exe') /s $dpFile | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Windows no pudo actualizar el inventario de discos. No se grabó nada.' }
    $disk = Assert-Target $imageBytes
    [System.IO.File]::WriteAllText($dpFile,"select disk $DiskNumber`r`nclean`r`nrescan`r`n",[System.Text.Encoding]::ASCII)
    & (Join-Path $env:SystemRoot 'System32\diskpart.exe') /s $dpFile | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Windows no pudo limpiar las particiones del USB. No se grabó la imagen.' }
    Remove-Item -LiteralPath $dpFile -Force
    $dpFile = $null
    $disk = Assert-Target $imageBytes
    # Diskpart can report an error yet return success on some Windows builds.
    # Removable Windows USB disks can remain reported as MBR after a successful
    # clean, even after Update-Disk. Check the empty layout, not its style label.
    if ($disk.NumberOfPartitions -ne 0) { throw 'Windows no limpió las particiones del USB. No se grabó la imagen.' }
    Emit-Json @{type='progress';stage='write';message='Grabando USB…'}
    $devicePath = "\\.\PhysicalDrive$DiskNumber"
    $chunkSize = 4 * 1024 * 1024
    $buffer = New-Object byte[] $chunkSize
    $diskStream = [System.IO.File]::Open($devicePath,[System.IO.FileMode]::Open,[System.IO.FileAccess]::ReadWrite,[System.IO.FileShare]::ReadWrite)
    # Keep this handle locked through readback: otherwise Windows can mount a
    # newly written FAT partition and deny raw writes partway through the image.
    $returned = [uint32]0
    if (-not [Aguja.WindowsDiskLock]::DeviceIoControl($diskStream.SafeFileHandle,0x00090018,[IntPtr]::Zero,0,[IntPtr]::Zero,0,[ref]$returned,[IntPtr]::Zero)) {
        throw 'Windows no pudo bloquear el USB para uso exclusivo. Cierra las aplicaciones que lo usan y vuelve a intentarlo. No se grabó la imagen.'
    }
    # Keep the partition table/boot headers unpublished until all payload bytes
    # are on the clean disk. New volumes otherwise evade the old raw lock.
    $headSize = [int][Math]::Min([long]$chunkSize,$imageBytes)
    $head = New-Object byte[] $headSize
    $headRead = $fileStream.Read($head,0,$headSize)
    if ($headRead -ne $headSize) { throw 'La cabecera de la imagen no pudo leerse por completo. No se grabó la imagen.' }
    $diskStream.Position = $headSize
    $written = [long]$headSize
    $lastReport = [DateTime]::UtcNow
    while ($written -lt $imageBytes) {
        Assert-Supervisor
        $toRead = [int][Math]::Min([long]$chunkSize,($imageBytes-$written))
        $bytesRead = $fileStream.Read($buffer,0,$toRead)
        if ($bytesRead -le 0) { throw 'La lectura de la imagen terminó antes de tiempo. El USB no está verificado.' }
        $diskStream.Write($buffer,0,$bytesRead)
        $written += $bytesRead
        if (([DateTime]::UtcNow-$lastReport).TotalMilliseconds -ge 500) {
            Emit-Json @{type='progress';stage='write';done=($written-$headSize);total=$imageBytes}
            $lastReport = [DateTime]::UtcNow
        }
    }
    Assert-Supervisor
    $diskStream.Position = 0
    $diskStream.Write($head,0,$headSize)
    $diskStream.Flush($true)
    Emit-Json @{type='progress';stage='write';done=$written;total=$imageBytes}
    $disk = Assert-Target $imageBytes
    Emit-Json @{type='progress';stage='readback';message='Verificando lectura del USB…'}
    $readStream = $diskStream
    $diskStream = $null
    $readStream.Position = 0
    $readShaAlg = [System.Security.Cryptography.SHA256]::Create()
    $verifiedBytes = [long]0
    $lastReport = [DateTime]::UtcNow
    while ($verifiedBytes -lt $imageBytes) {
        Assert-Supervisor
        $toRead = [int][Math]::Min([long]$chunkSize,($imageBytes-$verifiedBytes))
        $bytesRead = $readStream.Read($buffer,0,$toRead)
        if ($bytesRead -le 0) { throw 'La lectura del USB terminó antes de tiempo. La grabación no está verificada.' }
        $readShaAlg.TransformBlock($buffer,0,$bytesRead,$buffer,0) | Out-Null
        $verifiedBytes += $bytesRead
        if (([DateTime]::UtcNow-$lastReport).TotalMilliseconds -ge 500) {
            Emit-Json @{type='progress';stage='readback';done=$verifiedBytes;total=$imageBytes}
            $lastReport = [DateTime]::UtcNow
        }
    }
    $readShaAlg.TransformFinalBlock($buffer,0,0) | Out-Null
    $verifiedSha = [System.BitConverter]::ToString($readShaAlg.Hash).Replace('-','').ToLowerInvariant()
    if ($verifiedSha -ne $ExpectedSha256.ToLowerInvariant()) { throw 'La verificación de lectura del USB falló (SHA-256 no coincide).' }
    Emit-Json @{type='progress';stage='readback';done=$verifiedBytes;total=$imageBytes}
    Emit-Json @{ok=$true;verified=$true;device=$devicePath;serial=$ExpectedSerial;bytes=$written;sha256=$verifiedSha}
    $exitCode = 0
} catch {
    Emit-Json @{ok=$false;error=$_.Exception.Message}
} finally {
    foreach ($stream in @($fileStream,$diskStream,$readStream,$shaAlg,$readShaAlg)) {
        if ($null -ne $stream) { $stream.Dispose() }
    }
    if ($dpFile -and (Test-Path -LiteralPath $dpFile)) { Remove-Item -LiteralPath $dpFile -Force -ErrorAction SilentlyContinue }
}
exit $exitCode
