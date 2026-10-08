'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),{execFileSync}=require('node:child_process');
const modules=process.env.AGUJA_QA_MODULES||path.resolve(__dirname,'..');
const {windowsPowerShell,powershellArgs}=require(path.join(modules,'ai-tools.cjs'));

test('Windows raw writer publishes boot headers after payload and preserves every byte',{skip:process.platform!=='win32'},()=>{
 const source=fs.readFileSync(path.join(modules,'flash-windows.ps1'),'utf8');
 const body=source.match(/    # Keep the partition table\/boot headers[\s\S]*?    \$diskStream.Flush\(\$true\)/)?.[0];assert(body,'Actual write block missing');
 const script=String.raw`$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue'
Add-Type -TypeDefinition @'
using System;using System.IO;using System.Collections.Generic;
public class MountedRawDisk : MemoryStream {
    public readonly List<long> Offsets = new List<long>();
    private bool mounted;
    public MountedRawDisk(int size):base(new byte[size],true){}
    public void Flush(bool flushToDisk){base.Flush();}
    public override void Write(byte[] b,int o,int n){
        if(mounted && Position >= 1048576)throw new UnauthorizedAccessException("New volume denies subsequent raw writes");
        Offsets.Add(Position);base.Write(b,o,n);if(Offsets[Offsets.Count-1]==0)mounted=true;
    }
}
'@
function Assert-Supervisor {}
function Emit-Json($o) {if($o.done -gt $o.total){throw 'Progress exceeds total'}}
$sha=[Security.Cryptography.SHA256]::Create()
$results=@()
try {
 foreach($length in @(2097152,4194304,9437696)) {
    $data=New-Object byte[] $length
    (New-Object Random(32)).NextBytes($data)
    $fileStream=New-Object IO.MemoryStream(,$data)
    $diskStream=New-Object MountedRawDisk($length)
    $chunkSize=4*1024*1024
    $buffer=New-Object byte[] $chunkSize
    $imageBytes=[long]$length
    try {
`+body+String.raw`
        $actual=$diskStream.ToArray()
        if([BitConverter]::ToString($sha.ComputeHash($actual)) -cne [BitConverter]::ToString($sha.ComputeHash($data))){throw 'Image bytes changed'}
        if($diskStream.Offsets[-1] -ne 0){throw 'Boot headers not committed last'}
        if($length -gt $chunkSize -and $diskStream.Offsets[0] -ne $chunkSize){throw 'Partition table was published before payload'}
        $results+=@{bytes=$length;writes=$diskStream.Offsets.Count;verified=$true}
    } finally {$fileStream.Dispose();$diskStream.Dispose()}
 }
 ConvertTo-Json -Compress -InputObject @($results)
} finally {$sha.Dispose()}
`;
 const result=JSON.parse(execFileSync(windowsPowerShell(),powershellArgs(script),{encoding:'utf8',timeout:60000,windowsHide:true}).trim());
 assert.deepEqual(result,[{bytes:2097152,writes:1,verified:true},{bytes:4194304,writes:1,verified:true},{bytes:9437696,writes:3,verified:true}]);
});
