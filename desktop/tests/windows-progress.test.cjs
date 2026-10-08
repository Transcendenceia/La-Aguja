'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),{execFileSync}=require('node:child_process');
const modules=process.env.AGUJA_QA_MODULES||path.resolve(__dirname,'..');
const {LAUNCHER}=require(path.join(modules,'windows-flash.cjs'));
const {windowsPowerShell,powershellArgs}=require(path.join(modules,'ai-tools.cjs'));

test('Windows progress relay allows a concurrent writer and waits for complete UTF-8 JSONL records',{skip:process.platform!=='win32'},()=>{
 const reader=LAUNCHER.match(/function Read-Progress \{[\s\S]*?\n\}/)?.[0];assert(reader,'Progress reader missing');
 const script=String.raw`$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
`+reader+String.raw`
$progressPath=[System.IO.Path]::GetTempFileName()
$writer=$null
try {
    $utf8=New-Object System.Text.UTF8Encoding($false)
    $writer=[System.IO.File]::Open($progressPath,[System.IO.FileMode]::Open,[System.IO.FileAccess]::Write,[System.IO.FileShare]::ReadWrite)
    $originalDenied=$false
    try { [System.IO.File]::ReadAllLines($progressPath) | Out-Null }
    catch { $originalDenied=$true }
    if(-not $originalDenied){throw 'Original reader did not reproduce the sharing collision'}
    $first='{"type":"progress","message":"Comprobación"}'
    $bytes=$utf8.GetBytes($first+[char]13+[char]10)
    $cut=[Array]::IndexOf($bytes,[byte]0xc3)+1
    if($cut -le 0){throw 'UTF-8 fixture missing'}
    $writer.Write($bytes,0,$cut)
    $writer.Flush()
    if(@(Read-Progress).Count -ne 0){throw 'Partial UTF-8 record forwarded'}
    $writer.Write($bytes,$cut,$bytes.Length-$cut)
    $writer.Flush()
    $lines=@(Read-Progress)
    if($lines.Count -ne 1 -or $lines[0] -cne $first){throw 'Complete UTF-8 progress corrupted'}
    $second='{"ok":true,"verified":true}'
    $bytes=$utf8.GetBytes($second+[char]13+[char]10)
    $writer.Write($bytes,0,$bytes.Length-1)
    $writer.Flush()
    if(@(Read-Progress).Count -ne 1){throw 'Unterminated receipt forwarded'}
    $writer.Write($bytes,$bytes.Length-1,1)
    $writer.Flush()
    $lines=@(Read-Progress)
    if($lines.Count -ne 2 -or $lines[1] -cne $second){throw 'Final receipt lost'}
    @{ok=$true;completeRecords=$lines.Count;originalReaderDenied=$originalDenied} | ConvertTo-Json -Compress
} finally {
    if($writer){$writer.Dispose()}
    Remove-Item -LiteralPath $progressPath -Force
}
`;
 const result=JSON.parse(execFileSync(windowsPowerShell(),powershellArgs(script),{encoding:'utf8',timeout:30000,windowsHide:true}).trim());
 assert.deepEqual(result,{ok:true,completeRecords:2,originalReaderDenied:true});
});

test('Windows elevated progress writer coexists with the actual relay under repeated writes',{skip:process.platform!=='win32'},()=>{
 const reader=LAUNCHER.match(/function Read-Progress \{[\s\S]*?\n\}/)[0];
 const writerOpen=LAUNCHER.match(/        \$progressStream =[^\n]*\n        \$progressWriter =[^\n]*\n        \$progressWriter.AutoFlush =[^\n]*/)[0];
 const writerLine=LAUNCHER.match(/            \$progressWriter.WriteLine\(\[string\]\$_\)/)[0];
 const script=String.raw`$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
$progressPath=[IO.Path]::GetTempFileName()
`+reader+String.raw`
$worker=@'
param($progressPath)
$ErrorActionPreference='Stop'
try {
`+writerOpen+String.raw`
    1..2000 | ForEach-Object {$_='{"type":"progress","message":"Comprobación","done":'+$_+'}';
`+writerLine+String.raw`
    }
    $progressWriter.WriteLine('{"ok":true,"verified":true}')
} finally {if($progressWriter){$progressWriter.Dispose()}}
'@
$job=$null
try {
    $job=Start-Job -ScriptBlock ([scriptblock]::Create($worker)) -ArgumentList $progressPath
    $readerErrors=0
    while($job.State -eq 'Running'){try {@(Read-Progress)|Out-Null} catch {$readerErrors++}}
    Receive-Job $job -ErrorAction Stop|Out-Null
    if($job.State -ne 'Completed'){throw $job.ChildJobs[0].JobStateInfo.Reason}
    $lines=@(Read-Progress)
    if($lines.Count -ne 2001 -or $lines[-1] -cne '{"ok":true,"verified":true}'){throw 'Progress or receipt lost'}
    foreach($line in $lines){$line|ConvertFrom-Json|Out-Null}
    @{ok=$true;records=$lines.Count;readerErrors=$readerErrors}|ConvertTo-Json -Compress
} finally {
    if($job){Remove-Job $job -Force}
    Remove-Item -LiteralPath $progressPath -Force
}
`;
 const result=JSON.parse(execFileSync(windowsPowerShell(),powershellArgs(script),{encoding:'utf8',timeout:60000,windowsHide:true}).trim());
 assert.deepEqual(result,{ok:true,records:2001,readerErrors:0});
});
