'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),os=require('node:os'),{execFileSync}=require('node:child_process');
const modules=process.env.AGUJA_QA_MODULES||path.resolve(__dirname,'..');
const {LAUNCHER}=require(path.join(modules,'windows-flash.cjs')),{windowsPowerShell,powershellArgs,psQuote}=require(path.join(modules,'ai-tools.cjs'));
test('Windows bridge hardens Modify-only owned fixtures without changing owner or requesting ownership privileges',{skip:process.platform!=='win32'},()=>{
 const qaRoot=process.env.AGUJA_QA_ROOT||os.tmpdir();fs.mkdirSync(qaRoot,{recursive:true});
 const root=fs.mkdtempSync(path.join(qaRoot,'aguja-acl-regression-'));
 try{
  const start=LAUNCHER.indexOf('    # Preserve the owner'),end=LAUNCHER.indexOf('    $exe =',start);assert(start>=0&&end>start);
  const actualACL=LAUNCHER.slice(start,end).replaceAll('$PSScriptRoot','$fixture');
  const script=String.raw`$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
[Console]::OutputEncoding=New-Object System.Text.UTF8Encoding($false)
$fixture=`+psQuote(path.join(root,'modify-only'))+String.raw`
[System.IO.Directory]::CreateDirectory($fixture) | Out-Null
$fixtureOwnerSid=[System.Security.Principal.WindowsIdentity]::GetCurrent().User
$names=@('request.json','progress.jsonl','writer.ps1','launcher.ps1')
foreach($name in $names){[System.IO.File]::WriteAllText((Join-Path $fixture $name),'fixture')}
$objects=@($fixture)+@($names | ForEach-Object {Join-Path $fixture $_})
$owners=@{}
foreach($item in $objects){
    $owners[$item]=(Get-Acl -LiteralPath $item).Owner
    if($item -eq $fixture){
        $acl=New-Object System.Security.AccessControl.DirectorySecurity
        $acl.AddAccessRule((New-Object System.Security.AccessControl.FileSystemAccessRule($fixtureOwnerSid,'Modify','ContainerInherit,ObjectInherit','None','Allow')))
    }else{
        $acl=New-Object System.Security.AccessControl.FileSecurity
        $acl.AddAccessRule((New-Object System.Security.AccessControl.FileSystemAccessRule($fixtureOwnerSid,'Modify','Allow')))
    }
    $acl.SetAccessRuleProtection($true,$false)
    if($item -eq $fixture){[System.IO.Directory]::SetAccessControl($item,$acl)}else{[System.IO.File]::SetAccessControl($item,$acl)}
}
`+actualACL+String.raw`
$expected=@($fixtureOwnerSid.Value,'S-1-5-18','S-1-5-32-544') | Sort-Object
foreach($item in $objects){
    $acl=Get-Acl -LiteralPath $item
    if($acl.Owner -ne $owners[$item]){throw 'Owner changed'}
    if(-not $acl.AreAccessRulesProtected){throw 'ACL not protected'}
    $actual=@($acl.GetAccessRules($true,$true,[System.Security.Principal.SecurityIdentifier]) | ForEach-Object {
        if($_.AccessControlType -ne 'Allow' -or $_.FileSystemRights -ne 'FullControl'){throw 'Wrong access rule'}
        $_.IdentityReference.Value
    }) | Sort-Object
    if(($actual -join ',') -ne ($expected -join ',')){throw 'Unexpected principals'}
}
@{ok=$true;ownersPreserved=5;restrictedACLs=5} | ConvertTo-Json -Compress
`;
  const result=JSON.parse(execFileSync(windowsPowerShell(),powershellArgs(script),{encoding:'utf8',timeout:30000,windowsHide:true}).trim());
  assert.deepEqual(result,{ok:true,ownersPreserved:5,restrictedACLs:5});
 }finally{fs.rmSync(root,{recursive:true,force:true});}
});
