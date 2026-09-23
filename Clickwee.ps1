# Clickwee cursor helper for Windows 10/11 (no admin required)
#  -Install   : register clickwee:// link so the website can apply cursors
#  -Uri       : called by the browser, e.g. clickwee://apply/macOS-Black/Large
#  -Uninstall : remove link and restore original cursors
param([string]$Uri = "", [switch]$Install, [switch]$Uninstall,
      [string]$Theme = "", [string]$Size = "Regular", [switch]$Restore)

$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$ProgressPreference = "SilentlyContinue"

$home2     = Join-Path $env:LOCALAPPDATA "Clickwee"
$cache     = Join-Path $home2 "cache"
$backupReg = Join-Path $home2 "cursor-backup.reg"
$regPath   = "HKCU:\Control Panel\Cursors"
$proto     = "HKCU:\Software\Classes\clickwee"

$urls = @{
  "macOS-Black"     = "https://github.com/ful1e5/apple_cursor/releases/download/v2.0.1/macOS-Windows.zip"
  "macOS-White"     = "https://github.com/ful1e5/apple_cursor/releases/download/v2.0.1/macOS-White-Windows.zip"
  "XCursor-Dark"    = "https://github.com/ful1e5/XCursor-pro/releases/download/v2.0.2/XCursor-Pro-Dark-Windows.zip"
  "XCursor-Light"   = "https://github.com/ful1e5/XCursor-pro/releases/download/v2.0.2/XCursor-Pro-Light-Windows.zip"
  "GoogleDot-Black" = "https://github.com/ful1e5/Google_Cursor/releases/download/v2.0.0/GoogleDot-Black-Windows.zip"
  "GoogleDot-White" = "https://github.com/ful1e5/Google_Cursor/releases/download/v2.0.0/GoogleDot-White-Windows.zip"
}
$sizes = @("Regular","Large","Extra-Large")

Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System; using System.Runtime.InteropServices;
public class CursorApi {
  [DllImport("user32.dll", SetLastError=true)]
  public static extern bool SystemParametersInfo(uint a, uint b, IntPtr c, uint d);
}
"@
function Update-Cursors { [CursorApi]::SystemParametersInfo(0x57, 0, [IntPtr]::Zero, 0x03) | Out-Null }
function Say($msg, $icon = "Information") {
  [System.Windows.Forms.MessageBox]::Show($msg, "Clickwee", "OK", $icon) | Out-Null
}
function Backup {
  New-Item -ItemType Directory -Force -Path $home2 | Out-Null
  if (-not (Test-Path $backupReg)) { reg export "HKCU\Control Panel\Cursors" "$backupReg" /y | Out-Null }
}
function Restore-Original {
  if (Test-Path $backupReg) { reg import "$backupReg" 2>$null; Update-Cursors; return $true }
  return $false
}

function Apply-Theme($t, $s) {
  if (-not $urls.ContainsKey($t)) { throw "Unknown theme: $t" }
  if ($sizes -notcontains $s) { $s = "Regular" }
  Backup
  $pkg = Join-Path $cache $t
  if (-not (Test-Path $pkg)) {
    New-Item -ItemType Directory -Force -Path $cache | Out-Null
    $zip = "$pkg.zip"
    Invoke-WebRequest $urls[$t] -OutFile $zip -UseBasicParsing
    Expand-Archive $zip -DestinationPath $pkg -Force
    Remove-Item $zip -Force
  }
  $src = Get-ChildItem $pkg -Directory | Where-Object {
    $_.Name -like "*-$s-Windows" -and ($s -ne "Large" -or $_.Name -notlike "*Extra-Large*")
  } | Select-Object -First 1
  if (-not $src) { throw "Size '$s' not found for $t" }

  $map = [ordered]@{
    Arrow="Pointer","Default"; Help="Help"; AppStarting="Work"; Wait="Busy"; Crosshair="Cross"
    IBeam="Text","IBeam"; NWPen="Handwriting"; No="Unavailable","Unavailiable"
    SizeNS="Vert","Vertical"; SizeWE="Horz","Horizontal"
    SizeNWSE="Dgn1","Dng1","Diagonal_1"; SizeNESW="Dgn2","Dng2","Diagonal_2"
    SizeAll="Move"; UpArrow="Alternate"; Hand="Link"; Pin="Pin"; Person="Person"
  }
  $values = @()
  foreach ($role in $map.Keys) {
    $file = ""
    foreach ($n in $map[$role]) {
      foreach ($ext in ".cur",".ani") {
        $p = Join-Path $src.FullName "$n$ext"
        if (Test-Path $p) { $file = $p; break }
      }
      if ($file) { break }
    }
    Set-ItemProperty $regPath -Name $role -Value $file
    $values += $file
  }
  $scheme = "Clickwee $t ($s)"
  Set-ItemProperty $regPath -Name "(default)" -Value $scheme
  $schemes = "HKCU:\Control Panel\Cursors\Schemes"
  if (-not (Test-Path $schemes)) { New-Item $schemes -Force | Out-Null }
  Set-ItemProperty $schemes -Name $scheme -Value ($values -join ",")
  Update-Cursors
}

try {
  if ($Install) {
    New-Item -ItemType Directory -Force -Path $home2 | Out-Null
    $target = Join-Path $home2 "Clickwee.ps1"
    if ($PSCommandPath -ne $target) { Copy-Item $PSCommandPath $target -Force }
    Backup
    New-Item -Path $proto -Force | Out-Null
    Set-ItemProperty $proto -Name "(default)" -Value "URL:Clickwee"
    Set-ItemProperty $proto -Name "URL Protocol" -Value ""
    New-Item -Path "$proto\shell\open\command" -Force | Out-Null
    $cmd = "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$target`" -Uri `"%1`""
    Set-ItemProperty "$proto\shell\open\command" -Name "(default)" -Value $cmd
    Write-Host "Connected. Go back to the website and click Apply." -ForegroundColor Green
    return
  }
  if ($Uninstall) {
    Restore-Original | Out-Null
    Remove-Item $proto -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "Removed. Original cursors restored." -ForegroundColor Green
    return
  }
  if ($Uri) {
    $parts = ($Uri -replace '^clickwee:/*', '' -replace '[?#].*$', '').Trim('/') -split '/'
    if ($parts[0] -eq "uninstall") {
      Restore-Original | Out-Null
      Remove-Item $proto -Recurse -Force -ErrorAction SilentlyContinue
      Remove-Item $cache -Recurse -Force -ErrorAction SilentlyContinue
      Say "Clickwee 연결을 해제하고 원래 커서로 되돌렸습니다."
      return
    }
    if ($parts[0] -eq "restore") {
      if (-not (Restore-Original)) { Say "No backup found. Choose 'Windows Default' in Mouse settings." "Warning" }
      return
    }
    if ($parts[0] -eq "apply" -and $parts.Count -ge 2) {
      $s = "Regular"; if ($parts.Count -ge 3) { $s = $parts[2] }
      Apply-Theme $parts[1] $s
      return
    }
    throw "Invalid link: $Uri"
  }
  if ($Restore) { Restore-Original | Out-Null; return }
  if ($Theme) { Apply-Theme $Theme $Size; Write-Host "Done." -ForegroundColor Green; return }
} catch {
  if ($Uri) { Say ("Could not apply cursor.`n`n" + $_.Exception.Message) "Error" } else { throw }
}
