param([string]$RequestBase64)
$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue'
Add-Type -TypeDefinition 'using System;using System.Runtime.InteropServices;public static class AgujaConfigMove {[DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)]public static extern bool MoveFileEx(string from,string to,int flags);}'
$names=@('aguja-profile.json','aguja-recovery.json','locale.json','aguja.conf')
function Bytes($p){if(-not [IO.File]::Exists($p)){return $null};$f=Get-Item -LiteralPath $p -Force;if(($f.Attributes-band[IO.FileAttributes]::ReparsePoint)-ne 0-or$f.Length-gt4194304){throw 'File'};return ,[IO.File]::ReadAllBytes($p)}
function Hash($v){if($null-eq$v){return $null};$h=[Security.Cryptography.SHA256]::Create();try{return ([BitConverter]::ToString($h.ComputeHash([byte[]]$v))).Replace('-','').ToLower()}finally{$h.Dispose()}}
function Atomic($p,$v){$tmp=Join-Path ([IO.Path]::GetDirectoryName($p)) ('.aguja-'+[Guid]::NewGuid().ToString('N'));$f=[IO.FileStream]::new($tmp,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None);try{$f.Write($v,0,$v.Length);$f.Flush($true)}finally{$f.Dispose()};if(-not[AgujaConfigMove]::MoveFileEx($tmp,$p,9)){throw 'Atomic move'}}
function Recover($folder){$journal=Join-Path $folder 'aguja-config-transaction.json';$raw=Bytes $journal;if($null-eq$raw){return};$j=[Text.Encoding]::UTF8.GetString($raw)|ConvertFrom-Json;if($j.backup-notmatch'^aguja-config-backup-[a-f0-9]{32}$'){throw 'Journal'};if($j.state-eq'prepared'){foreach($n in $names){$expected=$j.original.$n;$p=Join-Path $folder $n;if($null-eq$expected){if(Test-Path -LiteralPath $p){[IO.File]::Delete($p)}}else{$v=Bytes (Join-Path (Join-Path $folder $j.backup) $n);if((Hash $v)-ne$expected){throw 'Backup'};Atomic $p $v}}};[IO.File]::Delete($journal)}
function Identify($r){$n=[int]([string]$r.device-replace'^\\\\\.\\PhysicalDrive','');if([string]$r.device-ne("\\.\PhysicalDrive"+$n)){throw 'Device'};$d=Get-Disk -Number $n;$serial=if($d.SerialNumber){$d.SerialNumber.Trim()}else{'USB-'+$n};if($d.BusType-ne'USB'-or$d.IsBoot-or$d.IsSystem-or$serial-ne$r.serial-or[int64]$d.Size-ne[int64]$r.size){throw 'Identity'};return $d}
$r=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($RequestBase64))|ConvertFrom-Json
$d=Identify $r
$parts=@(Get-Partition -DiskNumber $d.Number|Where-Object{try{$v=$_|Get-Volume;$v.FileSystemLabel-eq'AGUJA_CFG'-and$v.FileSystem-eq'FAT32'}catch{$false}})
if($parts.Count-ne1){throw 'CFG'};$part=$parts[0]
$own=$false;$folder=$null;$mutex=$null
try{
 if($part.DriveLetter){$folder=[string]$part.DriveLetter+':\'}else{$folder=Join-Path $env:TEMP ('aguja-config-mount-'+[Guid]::NewGuid().ToString('N'));[IO.Directory]::CreateDirectory($folder)|Out-Null;$folder+='\';Add-PartitionAccessPath -DiskNumber $d.Number -PartitionNumber $part.PartitionNumber -AccessPath $folder;$own=$true}
 $mutex=[IO.FileStream]::new((Join-Path $folder 'aguja-config.lock'),[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
 Recover $folder
 $marker=Bytes (Join-Path $folder 'release.json');if($null-eq$marker-or(([Text.Encoding]::UTF8.GetString($marker)|ConvertFrom-Json).features-notcontains'platform-profile-v1')){throw 'Release'}
 $old=@{};$hashes=[ordered]@{}
 # Cross-platform token is the hash of the exact stored files in sorted name order.
 foreach($n in @('aguja-profile.json','aguja-recovery.json','aguja.conf','locale.json')){$old[$n]=Bytes (Join-Path $folder $n);$hashes[$n]=Hash $old[$n]}
 # Python default JSON spacing contract, not PowerShell's different formatter.
 $tokens=@();foreach($n in $hashes.Keys){$val=if($null-eq$hashes[$n]){'null'}else{'"'+$hashes[$n]+'"'};$tokens+=('"'+$n+'": '+$val)};$token=Hash ([Text.Encoding]::UTF8.GetBytes('{'+($tokens-join', ')+'}'))
 if($r.operation-eq'read'){$files=@{};foreach($n in $names){if($null-ne$old[$n]){$files[$n]=[Convert]::ToBase64String($old[$n])}};@{ok=$true;files=$files;snapshot=$token}|ConvertTo-Json -Depth 8 -Compress;return}
 if($r.operation-ne'write'-or$r.snapshot-ne$token){throw 'Changed'}
 if(@($r.files.PSObject.Properties).Count-ne4){throw 'Names'};$new=@{};foreach($n in $names){$new[$n]=[Convert]::FromBase64String([string]$r.files.$n);if($new[$n].Length-gt4194304){throw 'Large'}}
 Identify $r|Out-Null
 $backup='aguja-config-backup-'+[Guid]::NewGuid().ToString('N');$dir=Join-Path $folder $backup;[IO.Directory]::CreateDirectory($dir)|Out-Null
 foreach($n in $names){if($null-ne$old[$n]){Atomic (Join-Path $dir $n) $old[$n]}}
 $journal=Join-Path $folder 'aguja-config-transaction.json';$j=@{schema=1;backup=$backup;state='prepared';original=$hashes}
 Atomic $journal ([Text.Encoding]::UTF8.GetBytes(($j|ConvertTo-Json -Depth 6 -Compress)))
 try{foreach($n in $names){Atomic (Join-Path $folder $n) $new[$n]};foreach($n in $names){if((Hash (Bytes (Join-Path $folder $n)))-ne(Hash $new[$n])){throw 'Readback'}};$j.state='committed';Atomic $journal ([Text.Encoding]::UTF8.GetBytes(($j|ConvertTo-Json -Depth 6 -Compress)));[IO.File]::Delete($journal)}catch{Recover $folder;throw}
 @{ok=$true;verified=$true;backup=$backup}|ConvertTo-Json -Compress
}finally{if($null-ne$mutex){$mutex.Dispose()};if($own){Remove-PartitionAccessPath -DiskNumber $d.Number -PartitionNumber $part.PartitionNumber -AccessPath $folder;[IO.Directory]::Delete($folder)}}
