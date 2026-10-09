# Read-only bridge. Requests arrive on stdin; private bytes return only through
# the parent-owned pipe. Never enumerate the vault, write credentials or log them.
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
try {
 Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class AgujaWinCred {
 [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
 public struct Credential {
  public uint Flags, Type; public string TargetName, Comment;
  public System.Runtime.InteropServices.ComTypes.FILETIME LastWritten;
  public uint BlobSize; public IntPtr Blob; public uint Persist, AttributeCount;
  public IntPtr Attributes; public string TargetAlias, UserName;
 }
 [DllImport("advapi32.dll", EntryPoint="CredReadW", CharSet=CharSet.Unicode, SetLastError=true)]
 public static extern bool Read(string target,uint type,uint flags,out IntPtr credential);
 [DllImport("advapi32.dll")] public static extern void CredFree(IntPtr buffer);
}
'@
 $request=[Console]::In.ReadToEnd()|ConvertFrom-Json
 if($request.provider -eq 'antigravity') {
  # Current agy shares gemini:antigravity with its desktop app; earlier
  # versions used a profile-path key. Consult only these provider entries.
  $profileRoot=[Environment]::GetEnvironmentVariable('USERPROFILE','Process')
  if(-not $profileRoot -or -not [IO.Path]::IsPathRooted($profileRoot)){throw 'Invalid profile'}
  if($request.store -eq 'current') {
   # Synthetic/overridden profiles must not accidentally read the real account.
   $actualRoot=[Environment]::GetFolderPath('UserProfile')
   if(-not [string]::Equals($profileRoot.TrimEnd('\'),$actualRoot.TrimEnd('\'),[StringComparison]::OrdinalIgnoreCase)) {
    @{status='missing'}|ConvertTo-Json -Compress;exit
   }
   $target='gemini:antigravity'
  } elseif(-not $request.store -or $request.store -eq 'legacy') {
   $target='gemini:'+[IO.Path]::Combine($profileRoot,'.gemini','jetski-standalone-oauth-token')
  } else {throw 'Invalid request'}
 } elseif($request.provider -eq 'codex' -and $request.target -match '^(cli\|[a-f0-9]{16}\.Codex Auth|secrets\|[a-f0-9]{16}\.codex)$') {
  $target=[string]$request.target
 } else { throw 'Invalid request' }
 $pointer=[IntPtr]::Zero
 if(-not [AgujaWinCred]::Read($target,1,0,[ref]$pointer)) {
  $code=[Runtime.InteropServices.Marshal]::GetLastWin32Error()
  if($code -eq 1168){ @{status='missing'}|ConvertTo-Json -Compress }
  else { @{status='unavailable'}|ConvertTo-Json -Compress }
 } else {
  $bytes=$null
  try {
   $credential=[Runtime.InteropServices.Marshal]::PtrToStructure($pointer,[type][AgujaWinCred+Credential])
   if($credential.BlobSize -eq 0 -or $credential.BlobSize -gt 524288){throw 'Invalid blob'}
   $bytes=New-Object byte[] $credential.BlobSize
   [Runtime.InteropServices.Marshal]::Copy($credential.Blob,$bytes,0,$bytes.Length)
   @{status='found';blob=[Convert]::ToBase64String($bytes)}|ConvertTo-Json -Compress
  } finally {
   if($bytes){[Array]::Clear($bytes,0,$bytes.Length)}
   [AgujaWinCred]::CredFree($pointer)
  }
 }
} catch { @{status='unavailable'}|ConvertTo-Json -Compress }
