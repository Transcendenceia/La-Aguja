'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),{execFileSync}=require('node:child_process');
const {windowsPowerShell,powershellArgs}=require('../ai-tools.cjs');
test('native Windows blank RAW/GPT disks need no volumes, populated-disk enumeration failures remain fatal',{skip:process.platform!=='win32'},()=>{
 const source=fs.readFileSync(path.resolve(__dirname,'../flash-windows.ps1'),'utf8'),helper=source.match(/function Get-TargetVolumes\(\$Disk\) \{[\s\S]*?\n\}/)?.[0];assert(helper);
 const script=String.raw`$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue'
`+helper+String.raw`
$script:calls=0;$script:fail=$false
function Get-Partition {[CmdletBinding()]param($DiskNumber);$script:calls++;if($script:fail){throw 'ENUMERATION_FAILED'};[pscustomobject]@{DiskNumber=$DiskNumber}}
function Get-Volume {param([Parameter(ValueFromPipeline=$true)]$Partition);process{[pscustomobject]@{UniqueId='fixture-volume'}}}
foreach($style in @('RAW','GPT')) {if(@(Get-TargetVolumes ([pscustomobject]@{Number=9;PartitionStyle=$style;NumberOfPartitions=0})).Count -ne 0){throw 'Blank disk has volumes'}}
if($script:calls -ne 0){throw 'Blank disk was enumerated'}
$disk=[pscustomobject]@{Number=9;PartitionStyle='GPT';NumberOfPartitions=1}
if(@(Get-TargetVolumes $disk).Count -ne 1 -or $script:calls -ne 1){throw 'Populated disk not enumerated'}
$script:fail=$true;$rejected=$false
try{Get-TargetVolumes $disk|Out-Null}catch{if($_.Exception.Message -ne 'ENUMERATION_FAILED'){throw};$rejected=$true}
if(-not $rejected){throw 'Enumeration failure ignored'}
@{ok=$true;blankStyles=2;populatedEnumerated=$true;enumerationFailureFatal=$true}|ConvertTo-Json -Compress
`;
 assert.deepEqual(JSON.parse(execFileSync(windowsPowerShell(),powershellArgs(script),{encoding:'utf8',windowsHide:true,timeout:30000}).trim()),{ok:true,blankStyles:2,populatedEnumerated:true,enumerationFailureFatal:true});
});
