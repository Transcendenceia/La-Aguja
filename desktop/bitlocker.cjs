'use strict';
const {runPowerShell}=require('./windows-privileged.cjs');

const STATUS_SCRIPT=String.raw`
$ErrorActionPreference='Stop'
$admin=([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if(-not $admin){@{available=$true;requiresElevation=$true;volumes=@()}|ConvertTo-Json -Compress;return}
try {
    $volumes=@(Get-BitLockerVolume -ErrorAction Stop | Where-Object {$_.VolumeStatus.ToString() -ne 'FullyDecrypted' -or $_.ProtectionStatus.ToString() -eq 'On'} | ForEach-Object {
        $recovery=($_.KeyProtector|Where-Object {$_.KeyProtectorType -eq 'RecoveryPassword'}|Select-Object -First 1)
        [PSCustomObject]@{
            mountPoint=$_.MountPoint
            volumeType=$_.VolumeType.ToString()
            volumeStatus=$_.VolumeStatus.ToString()
            protectionStatus=$_.ProtectionStatus.ToString()
            encryptionMethod=$_.EncryptionMethod.ToString()
            encryptionPercentage=[int]$_.EncryptionPercentage
            hasRecoveryPassword=[bool]$recovery
            keyProtectorId=if($recovery){$recovery.KeyProtectorId}else{''}
            capacityGB=[math]::Round($_.CapacityGB,2)
        }
    })
    @{available=$true;requiresElevation=$false;volumes=$volumes}|ConvertTo-Json -Depth 4 -Compress
} catch {
    @{available=$true;requiresElevation=$false;error='No se pudo comprobar BitLocker. Vuelve a intentarlo.';volumes=@()}|ConvertTo-Json -Compress
}
`;
async function getBitLockerStatus({authorize=false,query=runPowerShell,platform=process.platform}={}) {
  if(platform!=='win32')return {available:false,volumes:[],reason:'Plataforma no es Windows'};
  try {
    const result=JSON.parse(await query(STATUS_SCRIPT,{elevated:authorize===true}));
    if(result.ok===false)return {available:true,volumes:[],error:String(result.error||'No se pudo comprobar BitLocker. Vuelve a intentarlo.'),requiresElevation:Boolean(result.canceled),canceled:Boolean(result.canceled)};
    if(result.available!==true||!Array.isArray(result.volumes))throw Error('Invalid status');
    return {available:true,requiresElevation:Boolean(result.requiresElevation),...(result.error?{error:String(result.error)}:{}),volumes:result.volumes.map(v=>({
      mountPoint:cleanMountPoint(v.mountPoint),volumeType:String(v.volumeType||'Unknown'),volumeStatus:String(v.volumeStatus||'Unknown'),
      protectionStatus:String(v.protectionStatus||'Unknown'),encryptionMethod:String(v.encryptionMethod||'Unknown'),
      encryptionPercentage:Number(v.encryptionPercentage||0),hasRecoveryPassword:Boolean(v.hasRecoveryPassword),
      keyProtectorId:String(v.keyProtectorId||''),capacityGB:Number(v.capacityGB||0)
    }))};
  }catch{return {available:true,volumes:[],error:'No se pudo comprobar BitLocker. Vuelve a intentarlo.'};}
}

async function suspendBitLocker(mountPoint = 'C:', rebootCount = 1) {
  if (process.platform !== 'win32') {
    throw new Error('BitLocker solo está disponible en Windows.');
  }
  const cleanMount = cleanMountPoint(mountPoint);
  const count = Math.max(1, Math.min(15, parseInt(rebootCount, 10) || 1));
  const script = `
try {
    Suspend-BitLocker -MountPoint "${cleanMount}" -RebootCount ${count} -ErrorAction Stop
    $updated = Get-BitLockerVolume -MountPoint "${cleanMount}"
    [PSCustomObject]@{
        ok = $true
        mountPoint = "${cleanMount}"
        protectionStatus = $updated.ProtectionStatus.ToString()
        rebootCount = ${count}
    } | ConvertTo-Json
} catch {
    [PSCustomObject]@{
        ok = $false
        error = $_.Exception.Message
    } | ConvertTo-Json
}
  `;
  const raw = await runPowerShell(script,{elevated:true});
  const result = JSON.parse(raw);
  if (!result.ok) {
    throw new Error(result.error || 'No se pudo suspender BitLocker.');
  }
  return result;
}

async function resumeBitLocker(mountPoint = 'C:') {
  if (process.platform !== 'win32') {
    throw new Error('BitLocker solo está disponible en Windows.');
  }
  const cleanMount = cleanMountPoint(mountPoint);
  const script = `
try {
    Resume-BitLocker -MountPoint "${cleanMount}" -ErrorAction Stop
    $updated = Get-BitLockerVolume -MountPoint "${cleanMount}"
    [PSCustomObject]@{
        ok = $true
        mountPoint = "${cleanMount}"
        protectionStatus = $updated.ProtectionStatus.ToString()
    } | ConvertTo-Json
} catch {
    [PSCustomObject]@{
        ok = $false
        error = $_.Exception.Message
    } | ConvertTo-Json
}
  `;
  const raw = await runPowerShell(script,{elevated:true});
  const result = JSON.parse(raw);
  if (!result.ok) {
    throw new Error(result.error || 'No se pudo reanudar BitLocker.');
  }
  return result;
}

async function getRecoveryKey(mountPoint = 'C:') {
  if (process.platform !== 'win32') {
    throw new Error('BitLocker solo está disponible en Windows.');
  }
  const cleanMount = cleanMountPoint(mountPoint);
  const script = `
try {
    $bv = Get-BitLockerVolume -MountPoint "${cleanMount}" -ErrorAction Stop
    $recoveryKey = ($bv.KeyProtector | Where-Object { $_.KeyProtectorType -eq 'RecoveryPassword' } | Select-Object -First 1)
    if (-not $recoveryKey) {
        throw "No se encontró una contraseña de recuperación para ${cleanMount}."
    }
    [PSCustomObject]@{
        ok = $true
        mountPoint = "${cleanMount}"
        keyProtectorId = $recoveryKey.KeyProtectorId
        recoveryPassword = $recoveryKey.RecoveryPassword
        encryptionMethod = $bv.EncryptionMethod.ToString()
    } | ConvertTo-Json
} catch {
    [PSCustomObject]@{
        ok = $false
        error = $_.Exception.Message
    } | ConvertTo-Json
}
  `;
  const raw = await runPowerShell(script,{elevated:true});
  const result = JSON.parse(raw);
  if (!result.ok) {
    throw new Error(result.error || 'No se pudo obtener la clave de recuperación de BitLocker.');
  }
  return {
    mountPoint: result.mountPoint,
    keyProtectorId: result.keyProtectorId,
    recoveryPassword: result.recoveryPassword,
    encryptionMethod: result.encryptionMethod
  };
}

function cleanMountPoint(mp) {
  const m = String(mp || 'C:').trim().toUpperCase();
  if (!/^[A-Z]:?$/.test(m)) {
    throw new Error('Punto de montaje no válido. Usa C:, D:, etc.');
  }
  return m.endsWith(':') ? m : m + ':';
}

function buildBitLockerPayload(keys = []) {
  return {
    schema: 1,
    source: 'LA AGUJA Flash Imager (Windows)',
    exportedAt: new Date().toISOString(),
    volumes: keys.map(k => ({
      mountPoint: cleanMountPoint(k.mountPoint),
      keyProtectorId: String(k.keyProtectorId || ''),
      recoveryPassword: String(k.recoveryPassword || '').trim(),
      encryptionMethod: String(k.encryptionMethod || '')
    }))
  };
}

module.exports = {
  getBitLockerStatus,
  STATUS_SCRIPT,
  suspendBitLocker,
  resumeBitLocker,
  getRecoveryKey,
  cleanMountPoint,
  buildBitLockerPayload
};
