'use strict';
const fs=require('node:fs'),path=require('node:path');
const {windowsPowerShell}=require('./ai-tools.cjs');

// The elevated process receives only a launcher path. The request contains
// disk identity and image digest/path, never capsule contents or credentials.
const LAUNCHER=String.raw`param([switch]$Elevated)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$OutputEncoding = [Console]::OutputEncoding
# PS5.1's Out-Default/host may retain the OEM code page for redirected output.
# Write JSONL bytes directly instead of trusting host rendering of Write-Output.
$publicOutput = New-Object System.IO.StreamWriter([Console]::OpenStandardOutput(),(New-Object System.Text.UTF8Encoding($false)))
$publicOutput.AutoFlush = $true
$requestPath = Join-Path $PSScriptRoot 'request.json'
$progressPath = Join-Path $PSScriptRoot 'progress.jsonl'
$launchAttempted = $false
function Read-Progress {
    $stream = $null
    $reader = $null
    try {
        # ReadAllLines denies concurrent writes. Do not interrupt Add-Content
        # in the elevated process or count an unfinished JSONL record as seen.
        $stream = [System.IO.File]::Open($progressPath,[System.IO.FileMode]::Open,[System.IO.FileAccess]::Read,[System.IO.FileShare]::ReadWrite)
        $reader = New-Object System.IO.StreamReader($stream,[System.Text.Encoding]::UTF8,$true)
        $text = $reader.ReadToEnd()
        $lastNewline = $text.LastIndexOf([char]10)
        if ($lastNewline -ge 0) {
            foreach ($line in $text.Substring(0,$lastNewline).Split([char]10)) { $line.TrimEnd([char]13) }
        }
    } finally {
        if ($reader) { $reader.Dispose() } elseif ($stream) { $stream.Dispose() }
    }
}
if ($Elevated) {
    $progressWriter = $null
    try {
        # PS5.1 Add-Content can deny an existing reader even when that reader
        # permits writes. Keep one explicitly shared UTF-8 append handle.
        $progressStream = [System.IO.File]::Open($progressPath,[System.IO.FileMode]::Append,[System.IO.FileAccess]::Write,[System.IO.FileShare]::ReadWrite)
        $progressWriter = New-Object System.IO.StreamWriter($progressStream,(New-Object System.Text.UTF8Encoding($false)))
        $progressWriter.AutoFlush = $true
        $request = Get-Content -LiteralPath $requestPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $parameters = @{}
        foreach ($name in @('ImagePath','DiskNumber','ExpectedSerial','ExpectedSha256','ExpectedSize','ExpectedModel','SupervisorPID','ApplicationPID')) {
            $parameters[$name] = $request.$name
        }
        & (Join-Path $PSScriptRoot 'writer.ps1') @parameters | ForEach-Object {
            $progressWriter.WriteLine([string]$_)
        }
        exit $LASTEXITCODE
    } catch {
        if ($progressWriter) { $progressWriter.WriteLine((@{ok=$false;error='La grabación elevada de Windows no se completó.'} | ConvertTo-Json -Compress)) }
        exit 1
    } finally {
        if ($progressWriter) { $progressWriter.Dispose() }
    }
}
try {
    # Preserve the owner and grant only SYSTEM/Administrators alongside them.
    # Unix chmod does not protect private files on Windows.
    $owner = [System.Security.Principal.WindowsIdentity]::GetCurrent().User
    $acl = New-Object System.Security.AccessControl.DirectorySecurity
    $acl.SetAccessRuleProtection($true,$false)
    foreach ($sid in @($owner,(New-Object System.Security.Principal.SecurityIdentifier('S-1-5-18')),(New-Object System.Security.Principal.SecurityIdentifier('S-1-5-32-544')))) {
        $rule = New-Object System.Security.AccessControl.FileSystemAccessRule($sid,'FullControl','ContainerInherit,ObjectInherit','None','Allow')
        $acl.AddAccessRule($rule)
    }
    [System.IO.Directory]::SetAccessControl($PSScriptRoot,$acl)
    foreach ($name in @('request.json','progress.jsonl','writer.ps1','launcher.ps1')) {
        $fileAcl = New-Object System.Security.AccessControl.FileSecurity
        $fileAcl.SetAccessRuleProtection($true,$false)
        foreach ($sid in @($owner,(New-Object System.Security.Principal.SecurityIdentifier('S-1-5-18')),(New-Object System.Security.Principal.SecurityIdentifier('S-1-5-32-544')))) {
            $fileAcl.AddAccessRule((New-Object System.Security.AccessControl.FileSystemAccessRule($sid,'FullControl','Allow')))
        }
        [System.IO.File]::SetAccessControl((Join-Path $PSScriptRoot $name),$fileAcl)
    }
    $exe = Join-Path $PSHOME 'powershell.exe'
    $request = Get-Content -LiteralPath $requestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $request | Add-Member -NotePropertyName SupervisorPID -NotePropertyValue $PID
    [System.IO.File]::WriteAllText($requestPath,($request | ConvertTo-Json -Compress),(New-Object System.Text.UTF8Encoding($false)))
    $arguments = '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + $PSCommandPath + '" -Elevated'
    $launchAttempted = $true
    $child = Start-Process -FilePath $exe -ArgumentList $arguments -Verb RunAs -PassThru
    $seen = 0
    do {
        try {
            $lines = @(Read-Progress)
            while ($seen -lt $lines.Length) { $publicOutput.WriteLine($lines[$seen]); $seen++ }
        } catch { }
        if (-not $child.HasExited) { Start-Sleep -Milliseconds 200; $child.Refresh() }
    } while (-not $child.HasExited)
    # Flush the final receipt written just before the child exited.
    $lines = @(Read-Progress)
    while ($seen -lt $lines.Length) { $publicOutput.WriteLine($lines[$seen]); $seen++ }
    $child.WaitForExit()
    exit $child.ExitCode
} catch {
    $exception = $_.Exception
    while ($exception.InnerException) { $exception = $exception.InnerException }
    if ($exception.NativeErrorCode -eq 1223) {
        $reason = 'No se autorizó la grabación. Acepta el diálogo de permisos de Windows o vuelve a intentarlo.'
    } elseif ($launchAttempted) {
        $reason = 'No se pudo iniciar el grabador con permisos de Windows. No se ha verificado ninguna grabación.'
    } else {
        $reason = 'No se pudieron preparar los permisos privados del grabador de Windows. No se grabó nada.'
    }
    $publicOutput.WriteLine((@{ok=$false;error=$reason} | ConvertTo-Json -Compress))
    exit 1
}
`;

function requestFor(image,disk){
 const match=/^\\\\\.\\PhysicalDrive(\d+)$/i.exec(disk.device||'');
 if(!match||!Number.isSafeInteger(Number(match[1]))||!Number.isSafeInteger(disk.size)||disk.size<=0||typeof disk.serial!=='string'||!disk.serial||typeof disk.model!=='string'||!disk.model||!/^[a-f0-9]{64}$/i.test(image.sha256||''))throw new Error('La identidad del USB o imagen no es válida.');
 return {ImagePath:image.path,DiskNumber:Number(match[1]),ExpectedSerial:disk.serial,ExpectedSha256:image.sha256,ExpectedSize:disk.size,ExpectedModel:disk.model};
}
async function flashWindows({image,disk,directory,writer,run}){
 const request=requestFor(image,disk);
 // PowerShell can survive Electron's exit. The elevated writer must watch
 // both the UAC bridge and the application that owns the operation.
 request.ApplicationPID=process.pid;
 await fs.promises.mkdir(directory,{recursive:true,mode:0o700});
 const stage=await fs.promises.mkdtemp(path.join(directory,'windows-uac-'));
 try{
  await fs.promises.writeFile(path.join(stage,'writer.ps1'),'\ufeff'+(await fs.promises.readFile(writer,'utf8')).replace(/^\ufeff/,''),{flag:'wx',mode:0o600});
  await fs.promises.writeFile(path.join(stage,'request.json'),JSON.stringify(request),{flag:'wx',mode:0o600});
  await fs.promises.writeFile(path.join(stage,'progress.jsonl'),'',{flag:'wx',mode:0o600});
  await fs.promises.writeFile(path.join(stage,'launcher.ps1'),'\ufeff'+LAUNCHER,{flag:'wx',mode:0o600});
  return await run(windowsPowerShell(),['-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',path.join(stage,'launcher.ps1')],null,{timeout:4*60*60*1000,limit:4*1024*1024,phase:'flash'});
 }finally{await fs.promises.rm(stage,{recursive:true,force:true});}
}
module.exports={flashWindows,requestFor,LAUNCHER};
