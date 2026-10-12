# Only the currently connected WLAN profile. No localized netsh output, files,
# profile inventory, credential argv, or logs. Run through the private UAC broker.
$ErrorActionPreference='Stop'
try {
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class AgujaActiveWlan {
 [DllImport("wlanapi.dll")] static extern uint WlanOpenHandle(uint version, IntPtr reserved, out uint negotiated, out IntPtr client);
 [DllImport("wlanapi.dll")] static extern uint WlanEnumInterfaces(IntPtr client, IntPtr reserved, out IntPtr list);
 [DllImport("wlanapi.dll")] static extern uint WlanQueryInterface(IntPtr client, ref Guid guid, uint opcode, IntPtr reserved, out uint size, out IntPtr data, out uint type);
 [DllImport("wlanapi.dll", CharSet=CharSet.Unicode)] static extern uint WlanGetProfile(IntPtr client, ref Guid guid, string name, IntPtr reserved, out IntPtr xml, ref uint flags, out uint access);
 [DllImport("wlanapi.dll")] static extern void WlanFreeMemory(IntPtr data);
 [DllImport("wlanapi.dll")] static extern uint WlanCloseHandle(IntPtr client, IntPtr reserved);
 public static string Read() {
  IntPtr client=IntPtr.Zero, list=IntPtr.Zero;
  uint version;
  try {
   if(WlanOpenHandle(2,IntPtr.Zero,out version,out client)!=0)throw new Exception("unavailable");
   if(WlanEnumInterfaces(client,IntPtr.Zero,out list)!=0)throw new Exception("unavailable");
   int count=Marshal.ReadInt32(list); if(count<0 || count>64)throw new Exception("invalid");
   string profile=null; Guid active=Guid.Empty;
   for(int i=0;i<count;i++) {
    IntPtr item=IntPtr.Add(list,8+i*532);
    if(Marshal.ReadInt32(item,528)!=1)continue; // wlan_interface_state_connected
    Guid guid=(Guid)Marshal.PtrToStructure(item,typeof(Guid));
    IntPtr data=IntPtr.Zero;uint size,type;
    try {
     uint error=WlanQueryInterface(client,ref guid,7,IntPtr.Zero,out size,out data,out type);
     if(error!=0 || size<520)throw new Exception("unavailable");
     string name=Marshal.PtrToStringUni(IntPtr.Add(data,8),256).TrimEnd('\0');
     if(String.IsNullOrEmpty(name))throw new Exception("unavailable");
     if(profile!=null)throw new Exception("ambiguous");
     profile=name;active=guid;
    }finally{if(data!=IntPtr.Zero)WlanFreeMemory(data);}
   }
   if(profile==null)return null;
   IntPtr xml=IntPtr.Zero;uint flags=4,access;
   try {
    if(WlanGetProfile(client,ref active,profile,IntPtr.Zero,out xml,ref flags,out access)!=0)throw new Exception("unavailable");
    return Marshal.PtrToStringUni(xml);
   }finally{if(xml!=IntPtr.Zero)WlanFreeMemory(xml);}
  }finally{if(list!=IntPtr.Zero)WlanFreeMemory(list);if(client!=IntPtr.Zero)WlanCloseHandle(client,IntPtr.Zero);}
 }
}
'@
$raw=[AgujaActiveWlan]::Read()
if(!$raw){@{ok=$false;code='no-network'}|ConvertTo-Json -Compress;return}
$doc=[Xml.XmlDocument]::new();$doc.XmlResolver=$null;$doc.LoadXml($raw)
$ns=[Xml.XmlNamespaceManager]::new($doc.NameTable);$ns.AddNamespace('w',$doc.DocumentElement.NamespaceURI)
$ssidNode=$doc.SelectSingleNode('/w:WLANProfile/w:SSIDConfig/w:SSID/w:name',$ns)
$auth=$doc.SelectSingleNode('/w:WLANProfile/w:MSM/w:security/w:authEncryption/w:authentication',$ns).InnerText
$encryption=$doc.SelectSingleNode('/w:WLANProfile/w:MSM/w:security/w:authEncryption/w:encryption',$ns).InnerText
$useOneX=$doc.SelectSingleNode('/w:WLANProfile/w:MSM/w:security/w:authEncryption/w:useOneX',$ns)
if(!$ssidNode -or !$ssidNode.InnerText){throw 'unsupported'}
$security=$null;$key=''
if($useOneX -and $useOneX.InnerText -eq 'true'){throw 'unsupported'}
if($auth -eq 'open' -and $encryption -eq 'none'){$security='open'}
elseif($auth -in @('WPAPSK','WPA2PSK','WPA3SAE')){
 $security=if($auth -eq 'WPA3SAE'){'sae'}else{'wpa-psk'}
 $shared=$doc.SelectSingleNode('/w:WLANProfile/w:MSM/w:security/w:sharedKey',$ns)
 if(!$shared -or $shared.protected -ne 'false' -or !$shared.keyMaterial){@{ok=$false;code='key-unavailable'}|ConvertTo-Json -Compress;return}
 $key=[string]$shared.keyMaterial
}else{throw 'unsupported'}
$hiddenNode=$doc.SelectSingleNode('/w:WLANProfile/w:SSIDConfig/w:nonBroadcast',$ns)
@{ok=$true;wifi=@{ssid=$ssidNode.InnerText;password=$key;security=$security;country='ES';hidden=($hiddenNode -and $hiddenNode.InnerText -eq 'true')}}|ConvertTo-Json -Compress -Depth 4
}catch{@{ok=$false;code='unavailable'}|ConvertTo-Json -Compress}
