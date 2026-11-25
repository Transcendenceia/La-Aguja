param(
  [Parameter(Mandatory=$true)]
  [ValidateSet('list-ports', 'verify-boot')]
  [string]$Action,
  [string]$Port = '',
  [int]$TimeoutSeconds = 24
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding

function Emit-Json($obj) {
  [Console]::Out.WriteLine(($obj | ConvertTo-Json -Depth 6 -Compress))
  [Console]::Out.Flush()
}

if ($Action -eq 'list-ports') {
  $items = @()
  $seen = @{}
  try {
    $pnp = Get-CimInstance -ClassName Win32_PnPEntity -ErrorAction Stop |
      Where-Object { $_.Name -and $_.Name -match '\((COM\d+)\)' }
    foreach ($dev in $pnp) {
      if ($dev.Name -match '\((COM\d+)\)') {
        $com = $Matches[1].ToUpperInvariant()
        if ($seen.ContainsKey($com)) { continue }
        $seen[$com] = $true
        $pnpId = [string]($dev.PNPDeviceID)
        $vid = ''
        $pidVal = ''
        if ($pnpId -match 'VID_([0-9A-Fa-f]{4})') { $vid = $Matches[1].ToLowerInvariant() }
        if ($pnpId -match 'PID_([0-9A-Fa-f]{4})') { $pidVal = $Matches[1].ToLowerInvariant() }
        $serial = ''
        $parts = $pnpId -split '\\'
        if ($parts.Length -ge 3) { $serial = $parts[2] }
        $label = ($dev.Name -replace '\s*\(COM\d+\)\s*$', '').Trim()
        $okStatus = (-not $dev.Status) -or ($dev.Status -eq 'OK')
        $items += [PSCustomObject]@{
          path = $com
          name = $com
          byId = $pnpId
          vid = $vid
          pid = $pidVal
          usbId = if ($vid -and $pidVal) { "$vid`:$pidVal" } else { '' }
          product = if ($label) { $label } else { 'USB Serial' }
          manufacturer = [string]($dev.Manufacturer)
          serial = $serial
          accessible = [bool]$okStatus
        }
      }
    }
  } catch {}

  # Fallback: include any COM ports exposed only via .NET SerialPort registry
  try {
    foreach ($name in [System.IO.Ports.SerialPort]::GetPortNames()) {
      $com = $name.Trim().ToUpperInvariant()
      if ($com -match '^COM\d+$' -and -not $seen.ContainsKey($com)) {
        $seen[$com] = $true
        $items += [PSCustomObject]@{
          path = $com
          name = $com
          byId = ''
          vid = ''
          pid = ''
          usbId = ''
          product = 'Serial Port'
          manufacturer = ''
          serial = ''
          accessible = $true
        }
      }
    }
  } catch {}

  Emit-Json @{ ok = $true; ports = $items }
  exit 0
}

if ($Action -eq 'verify-boot') {
  if ($Port -notmatch '^COM\d+$') {
    Emit-Json @{ ok = $false; error = 'Puerto COM no válido.' }
    exit 1
  }
  $result = [ordered]@{
    booted = $false
    provisioned_from_nvs = $false
    wifi_ip = ''
    tailnet_state = ''
    vpn_ip = ''
    hostname = ''
    fw_version = ''
    board = ''
    chip = ''
  }

  $sp = $null
  try {
    $sp = [System.IO.Ports.SerialPort]::new($Port, 115200, [System.IO.Ports.Parity]::None, 8, [System.IO.Ports.StopBits]::One)
    $sp.ReadTimeout = 350
    $sp.WriteTimeout = 1000
    $sp.DtrEnable = $false
    $sp.RtsEnable = $false
    $sp.NewLine = "`n"
    $sp.Open()

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $lastPoll = -10.0
    $buf = ''

    while ($sw.Elapsed.TotalSeconds -lt $TimeoutSeconds) {
      try {
        $chunk = $sp.ReadExisting()
        if ($chunk) {
          $buf += $chunk
          while ($buf.Contains("`n")) {
            $idx = $buf.IndexOf("`n")
            $line = $buf.Substring(0, $idx).Trim()
            $buf = $buf.Substring($idx + 1)
            if (-not $line) { continue }
            if ($line -match 'AGUJA-IOT Mobile Ops Center|Boot complete') { $result.booted = $true }
            if ($line -match 'Provisioned config from NVS init_json') { $result.provisioned_from_nvs = $true }
            if ($line -match 'got ip:(\d+\.\d+\.\d+\.\d+)') { $result.wifi_ip = $Matches[1] }
            if ($line -match 'Tailscale CONNECTED|tailnet=CONNECTED') { $result.tailnet_state = 'CONNECTED' }
            if ($line -match 'vpn=(\d+\.\d+\.\d+\.\d+)' -and $Matches[1] -ne '0.0.0.0') { $result.vpn_ip = $Matches[1] }
            if ($line.StartsWith('{') -and $line.EndsWith('}')) {
              try {
                $obj = $line | ConvertFrom-Json -ErrorAction Stop
                if ($null -ne $obj.wifi -or $null -ne $obj.tailnet -or $null -ne $obj.tailnet_state -or $null -ne $obj.wifi_ip) {
                  $result.booted = $true
                  $wip = if ($obj.wifi_ip) { [string]$obj.wifi_ip } elseif ($obj.wifi -and $obj.wifi.ip) { [string]$obj.wifi.ip } else { '' }
                  if ($wip -and $wip -ne '0.0.0.0') { $result.wifi_ip = $wip }
                  $vip = if ($obj.vpn_ip) { [string]$obj.vpn_ip } elseif ($obj.tailnet -and $obj.tailnet.vpn_ip) { [string]$obj.tailnet.vpn_ip } else { '' }
                  if ($vip -and $vip -ne '0.0.0.0') { $result.vpn_ip = $vip }
                  if ($obj.tailnet_state) { $result.tailnet_state = [string]$obj.tailnet_state }
                  elseif ($obj.tailnet -and $null -ne $obj.tailnet.connected) { $result.tailnet_state = if ($obj.tailnet.connected) { 'CONNECTED' } else { 'CONNECTING' } }
                  $hn = if ($obj.hostname) { [string]$obj.hostname } elseif ($obj.tailnet -and $obj.tailnet.hostname) { [string]$obj.tailnet.hostname } else { '' }
                  if ($hn) { $result.hostname = $hn }
                  if ($obj.board) { $result.board = [string]$obj.board }
                  if ($obj.chip) { $result.chip = [string]$obj.chip }
                }
              } catch {}
            }
          }
        }
      } catch {}

      $elapsed = $sw.Elapsed.TotalSeconds
      if ($elapsed -ge 3.5 -and ($elapsed - $lastPoll) -ge 2.5) {
        $lastPoll = $elapsed
        try { $sp.Write("status`n") } catch {}
        if ($result.vpn_ip -and $result.tailnet_state -eq 'CONNECTED') { break }
      }
      Start-Sleep -Milliseconds 150
    }
  } catch {
    $result.warning = "No se pudo abrir $Port tras grabar: $($_.Exception.Message)"
  } finally {
    if ($sp -and $sp.IsOpen) { try { $sp.Close() } catch {} }
  }

  Emit-Json @{ ok = $true; boot = $result }
  exit 0
}
