'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),{spawn,execFileSync}=require('node:child_process');
const modules=process.env.AGUJA_QA_MODULES||path.resolve(__dirname,'..');
const {windowsPowerShell,powershellArgs}=require(path.join(modules,'ai-tools.cjs'));

// Execute the actual writer guard against real live/dead processes, with no
// disk enumeration, image handles, elevation, or device access.
test('Windows writer refuses an orphaned launcher or application before continuing',{skip:process.platform!=='win32'},async()=>{
 const source=fs.readFileSync(path.join(modules,'flash-windows.ps1'),'utf8');
 const guard=source.match(/function Assert-Supervisor \{[\s\S]*?\n\}/)?.[0];assert(guard,'Writer watchdog function missing');
 const departed=spawn(process.execPath,['-e',''],{windowsHide:true,stdio:'ignore'});
 const departedPID=departed.pid;assert(Number.isInteger(departedPID));
 await new Promise((resolve,reject)=>{departed.on('error',reject);departed.on('exit',resolve);});
 const script=String.raw`$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
`+guard+String.raw`
$live=`+process.pid+String.raw`
$departed=`+departedPID+String.raw`
$SupervisorPID=$live
$ApplicationPID=$live
Assert-Supervisor
$failures=0
foreach($pair in @(@($live,$departed),@($departed,$live))){
    $SupervisorPID=$pair[0]
    $ApplicationPID=$pair[1]
    try { Assert-Supervisor; throw 'WATCHDOG_DID_NOT_STOP' }
    catch {
        if($_.Exception.Message -notmatch 'La aplicación se cerró'){throw}
        $failures++
    }
}
@{ok=$true;deadProcessesRejected=$failures} | ConvertTo-Json -Compress
`;
 const result=JSON.parse(execFileSync(windowsPowerShell(),powershellArgs(script),{encoding:'utf8',timeout:30000,windowsHide:true}).trim());
 assert.deepEqual(result,{ok:true,deadProcessesRejected:2});
});
