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
$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$OutputEncoding = [Console]::OutputEncoding
$fileStream = $null
$diskStream = $null
$readStream = $null
$shaAlg = $null
$readShaAlg = $null
$volumeHandles = New-Object 'System.Collections.Generic.List[Microsoft.Win32.SafeHandles.SafeFileHandle]'
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
function Get-TargetVolumes($Disk) {
    # Storage cmdlets report ObjectNotFound on a blank RAW disk (and on an
    # initialized disk with no partitions). That is a valid flash target,
    # not an enumeration failure. Keep failures on populated disks fatal.
    if ($Disk.PartitionStyle -eq 'RAW' -or $Disk.NumberOfPartitions -eq 0) { return }
    Get-Partition -DiskNumber $Disk.Number -ErrorAction Stop |
        Get-Volume -ErrorAction SilentlyContinue | Where-Object {$_.UniqueId}
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
using System.ComponentModel;
using System.Text;
using Microsoft.Win32.SafeHandles;
namespace Aguja {
    public static class WindowsDiskLock {
        [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
        static extern SafeFileHandle CreateFile(string path, uint access, uint share, IntPtr security, uint creation, uint flags, IntPtr template);
        public static SafeFileHandle OpenVolume(string path) {
            var handle=CreateFile(path.TrimEnd('\\'),0xC0000000,3,IntPtr.Zero,3,0,IntPtr.Zero);
            if(handle.IsInvalid){handle.Dispose();throw new InvalidOperationException("Windows no pudo abrir un volumen del USB para liberarlo.");}
            return handle;
        }
        public static bool Control(SafeFileHandle h,uint code){uint returned;return DeviceIoControl(h,code,IntPtr.Zero,0,IntPtr.Zero,0,out returned,IntPtr.Zero);}
        [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
        static extern uint GetFinalPathNameByHandle(SafeFileHandle h,StringBuilder path,uint size,uint flags);
        public static string FinalVolumePath(SafeFileHandle h){var path=new StringBuilder(32768);uint count=GetFinalPathNameByHandle(h,path,(uint)path.Capacity,1);if(count==0||count>=path.Capacity)throw new InvalidOperationException("No se pudo comprobar la ubicación de la imagen antes de liberar el USB.");return path.ToString();}
        [StructLayout(LayoutKind.Sequential)] public struct UniqueProcess { public uint ProcessId; public System.Runtime.InteropServices.ComTypes.FILETIME StartTime; }
        [StructLayout(LayoutKind.Sequential,CharSet=CharSet.Unicode)] public struct ProcessInfo {
            public UniqueProcess Process;
            [MarshalAs(UnmanagedType.ByValTStr,SizeConst=256)] public string AppName;
            [MarshalAs(UnmanagedType.ByValTStr,SizeConst=64)] public string ServiceName;
            public int AppType; public uint AppStatus; public uint SessionId;
            [MarshalAs(UnmanagedType.Bool)] public bool Restartable;
        }
        [DllImport("rstrtmgr.dll",CharSet=CharSet.Unicode)] static extern int RmStartSession(out uint session,uint flags,StringBuilder key);
        [DllImport("rstrtmgr.dll")] static extern int RmEndSession(uint session);
        [DllImport("rstrtmgr.dll",CharSet=CharSet.Unicode)] static extern int RmRegisterResources(uint session,uint fileCount,string[] files,uint appCount,UniqueProcess[] apps,uint serviceCount,string[] services);
        [DllImport("rstrtmgr.dll")] static extern int RmGetList(uint session,out uint needed,ref uint count,[In,Out] ProcessInfo[] processes,out uint reasons);
        [DllImport("rstrtmgr.dll")] static extern int RmShutdown(uint session,uint flags,IntPtr callback);
        static string[] VolumeFiles(string root) {
            var files=new System.Collections.Generic.List<string>();var directories=new System.Collections.Generic.Stack<string>();directories.Push(root);
            var deadline=DateTime.UtcNow.AddSeconds(20);
            while(directories.Count>0) {
                if(DateTime.UtcNow>deadline||files.Count>50000)break;
                string directory=directories.Pop();
                try { foreach(string file in System.IO.Directory.EnumerateFiles(directory)) { if((System.IO.File.GetAttributes(file)&System.IO.FileAttributes.ReparsePoint)==0)files.Add(file);if(files.Count>50000)break; } }
                catch(System.IO.IOException){}catch(UnauthorizedAccessException){}
                try {foreach(string child in System.IO.Directory.EnumerateDirectories(directory)){if((System.IO.File.GetAttributes(child)&System.IO.FileAttributes.ReparsePoint)==0)directories.Push(child);}}
                catch(System.IO.IOException){}catch(UnauthorizedAccessException){}
            }
            return files.ToArray();
        }
        public static int ReleaseApplications(string root,int[] protectedPids) {
            string[] files=VolumeFiles(root);if(files.Length==0)return 0;
            uint session=0,closeSession=0;var key=new StringBuilder(Guid.NewGuid().ToString("N"));
            if(RmStartSession(out session,0,key)!=0)return 0;
            try {
                for(int start=0;start<files.Length;start+=500){int count=Math.Min(500,files.Length-start);var batch=new string[count];Array.Copy(files,start,batch,0,count);if(RmRegisterResources(session,(uint)count,batch,0,null,0,null)!=0)return 0;}
                ProcessInfo[] found=null;uint required=0,number=0,reasons=0;
                for(int attempt=0;attempt<4;attempt++){int status=RmGetList(session,out required,ref number,found,out reasons);if(status==0)break;if(status!=234||required>1024)return 0;number=required;found=new ProcessInfo[number];}
                if(found==null||number==0)return 0;
                var allowed=new System.Collections.Generic.List<UniqueProcess>();
                for(int n=0;n<number;n++){
                    var app=found[n];bool protectedApp=app.Process.ProcessId<=4||app.AppType==3||app.AppType==4||app.AppType==1000;
                    foreach(int id in protectedPids)if(id>0&&app.Process.ProcessId==(uint)id)protectedApp=true;
                    if(!protectedApp&&(app.AppType==1||app.AppType==2||app.AppType==5)&&String.IsNullOrEmpty(app.ServiceName))allowed.Add(app.Process);
                }
                if(allowed.Count==0)return 0;
                key=new StringBuilder(Guid.NewGuid().ToString("N"));if(RmStartSession(out closeSession,0,key)!=0)return 0;
                if(RmRegisterResources(closeSession,0,null,(uint)allowed.Count,allowed.ToArray(),0,null)!=0)return 0;
                // Ask eligible USB users to save and close; never force-kill an
                // unresponsive app, an unrelated process, Explorer or a service.
                RmShutdown(closeSession,0,IntPtr.Zero);return allowed.Count;
            } finally {if(closeSession!=0)RmEndSession(closeSession);RmEndSession(session);}
        }
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
    # Revalidate exact USB identity before releasing any owner handles.
    $disk = Assert-Target $imageBytes
    Emit-Json @{type='progress';stage='exclusive';message='Liberando volúmenes del USB para uso exclusivo…'}
    $volumes = @(Get-TargetVolumes $disk)
    $sourceVolumePath = [Aguja.WindowsDiskLock]::FinalVolumePath($fileStream.SafeFileHandle)
    foreach ($volume in $volumes) {
        if ($sourceVolumePath.StartsWith([string]$volume.UniqueId,[StringComparison]::OrdinalIgnoreCase)) { throw 'La imagen que se va a grabar está dentro del USB seleccionado. Elige otra unidad de trabajo; no se borró nada.' }
    }
    $letters = @($volumes | Where-Object {$_.DriveLetter} | ForEach-Object {([string]$_.DriveLetter).ToUpperInvariant() + ':'})
    if ($letters -contains [IO.Path]::GetPathRoot($PSScriptRoot).TrimEnd('\').ToUpperInvariant()) { throw 'El grabador está dentro del USB seleccionado. Mueve la aplicación a otra unidad; no se borró nada.' }
    if ($letters.Length -gt 0) {
        # Only Explorer windows showing this USB; never kill Explorer globally.
        try {
            $shell = New-Object -ComObject Shell.Application
            foreach ($window in @($shell.Windows())) {
                try {
                    $url = [Uri]$window.LocationURL
                    if ($url.IsFile -and $url.LocalPath.Length -ge 2 -and $letters -contains $url.LocalPath.Substring(0,2).ToUpperInvariant()) { $window.Quit() }
                } catch { }
            }
        } catch { }
    }
    foreach ($volume in $volumes) {
        Assert-Supervisor
        $handle = [Aguja.WindowsDiskLock]::OpenVolume([string]$volume.UniqueId)
        $volumeHandles.Add($handle)
        if (-not [Aguja.WindowsDiskLock]::Control($handle,0x00090018)) {
            $root = if($volume.DriveLetter){([string]$volume.DriveLetter)+':\'}else{[string]$volume.UniqueId}
            [Aguja.WindowsDiskLock]::ReleaseApplications($root,[int[]]@($PID,$ApplicationPID,$SupervisorPID)) | Out-Null
            if ([Aguja.WindowsDiskLock]::Control($handle,0x00090018)) {
                if (-not [Aguja.WindowsDiskLock]::Control($handle,0x00090020)) { throw 'Windows no pudo desmontar el volumen bloqueado del USB. No se borró nada.' }
                continue
            }
            # The selected USB will be overwritten. Dismount invalidates open
            # files on that volume, not processes/documents on other disks.
            if (-not [Aguja.WindowsDiskLock]::Control($handle,0x00090020)) {
                throw 'Windows no pudo liberar un volumen del USB. Otra aplicación mantiene un bloqueo exclusivo. No se borró nada.'
            }
            $locked = $false
            for ($attempt=0; $attempt -lt 50; $attempt++) {
                Assert-Supervisor
                if ([Aguja.WindowsDiskLock]::Control($handle,0x00090018)) { $locked=$true; break }
                Start-Sleep -Milliseconds 100
            }
            if (-not $locked) { throw 'Windows no pudo obtener acceso exclusivo al USB después de desmontarlo. No se borró nada.' }
        }
        if (-not [Aguja.WindowsDiskLock]::Control($handle,0x00090020)) { throw 'Windows no pudo desmontar el volumen bloqueado del USB. No se borró nada.' }
    }
    $disk = Assert-Target $imageBytes
    $devicePath = "\\.\PhysicalDrive$DiskNumber"
    # An exclusive raw handle is required BEFORE any destructive change.
    try { $diskStream = [System.IO.File]::Open($devicePath,[System.IO.FileMode]::Open,[System.IO.FileAccess]::ReadWrite,[System.IO.FileShare]::None) }
    catch { throw 'Windows no pudo reservar el USB en exclusiva. Otra herramienta mantiene un acceso directo al disco. No se borró nada.' }
    Emit-Json @{type='progress';stage='write';message='Limpiando particiones del USB…'}
    $chunkSize = 4 * 1024 * 1024
    $buffer = New-Object byte[] $chunkSize
    # DELETE_DRIVE_LAYOUT can recreate a removable-media device object and
    # invalidate the raw handle (ERROR_NO_SUCH_DEVICE on real JetFlash USBs).
    # Invalidate primary and backup partition headers through the already
    # exclusive stream instead, without publishing a new layout mid-write.
    $wipeSize = [int][Math]::Min([long]$chunkSize,[long]$ExpectedSize)
    $diskStream.Position = 0
    $diskStream.Write($buffer,0,$wipeSize)
    $diskStream.Position = $ExpectedSize - $wipeSize
    $diskStream.Write($buffer,0,$wipeSize)
    $diskStream.Flush($true)
    Emit-Json @{type='progress';stage='write';message='Grabando USB…'}
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
    Emit-Json @{ok=$false;error=$_.Exception.GetBaseException().Message}
} finally {
    foreach ($stream in @($fileStream,$diskStream,$readStream,$shaAlg,$readShaAlg)) {
        if ($null -ne $stream) { $stream.Dispose() }
    }
    foreach ($handle in $volumeHandles) { $handle.Dispose() }
}
exit $exitCode
