# Clickwee cursor helper for Windows 10/11 (no admin required)
#  -Install   : register clickwee:// link so the website can apply cursors
#  -Uri       : called by the browser, e.g. clickwee://apply/Bibata-Modern-Classic/Large
#               (the theme is looked up in catalog.json, built by tools/build_catalog.py)
#  -Uninstall : remove link and restore original cursors
#  -Theme X [-Size Regular|Large|Extra-Large] : apply directly (for testing)
# This file is embedded in Clickwee-Connect.bat by tools/build_connect.py.
param([string]$Uri = "", [switch]$Install, [switch]$Uninstall,
      [string]$Theme = "", [string]$Size = "Regular", [switch]$Restore)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]'Tls13' }
catch { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 }

$Version   = 3
$home2     = Join-Path $env:LOCALAPPDATA "Clickwee"
$cache     = Join-Path $home2 "cache"
$backupJs  = Join-Path $home2 "cursor-backup.json"
$backupReg = Join-Path $home2 "cursor-backup.reg"   # written by v1
$cursorKey = "Control Panel\Cursors"
$proto     = "HKCU:\Software\Classes\clickwee"
$uninstKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\Clickwee"

# The theme list lives in catalog.json on the website, so new cursors work without
# re-running the connect file. Downloads are only accepted from these places.
$catalogUrls = @(
  "https://raw.githubusercontent.com/Alexversify/clickwee/main/catalog.json",
  "https://cdn.jsdelivr.net/gh/Alexversify/clickwee@main/catalog.json",
  "https://clickwee.com/catalog.json"
)
$allowed = '^https://(github\.com/|raw\.githubusercontent\.com/Alexversify/clickwee/|cdn\.jsdelivr\.net/gh/Alexversify/clickwee@)'
$catalogFile = Join-Path $home2 "catalog.json"
$sizes = @("Regular","Large","Extra-Large")

# Windows role = file names used by the ful1e5 builds (spellings vary per project)
$map = [ordered]@{
  Arrow="Pointer","Default"; Help="Help"; AppStarting="Work"; Wait="Busy"; Crosshair="Cross"
  IBeam="Text","IBeam"; NWPen="Handwriting"; No="Unavailable","Unavailiable"
  SizeNS="Vert","Vertical"; SizeWE="Horz","Horizontal"
  SizeNWSE="Dgn1","Dng1","Diagonal_1"; SizeNESW="Dgn2","Dng2","Diagonal_2"
  SizeAll="Move"; UpArrow="Alternate"; Hand="Link"; Pin="Pin"; Person="Person"
}

Add-Type -AssemblyName System.Windows.Forms, System.Drawing, System.IO.Compression.FileSystem
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
$script:tray = $null
function Notify($msg) {
  try {
    if (-not $script:tray) {
      $script:tray = New-Object System.Windows.Forms.NotifyIcon
      $script:tray.Icon = [System.Drawing.SystemIcons]::Information
      $script:tray.Text = "Clickwee"
      $script:tray.Visible = $true
    }
    $script:tray.ShowBalloonTip(3000, "Clickwee", $msg, "Info")
  } catch {}
}
function Close-Tray { if ($script:tray) { Start-Sleep -Seconds 3; $script:tray.Dispose() } }

# --- backup / restore of HKCU\Control Panel\Cursors (keeps REG_EXPAND_SZ intact) ---
function Backup {
  New-Item -ItemType Directory -Force -Path $home2 | Out-Null
  if ((Test-Path $backupJs) -or (Test-Path $backupReg)) { return }
  $k = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey($cursorKey)
  $vals = @()
  foreach ($n in $k.GetValueNames()) {
    $kind = $k.GetValueKind($n)
    if ($kind -ne "String" -and $kind -ne "ExpandString" -and $kind -ne "DWord") { continue }
    $v = $k.GetValue($n, $null, [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames)
    $vals += [pscustomobject]@{ name = $n; kind = "$kind"; value = "$v" }
  }
  $k.Close()
  [IO.File]::WriteAllText($backupJs, (ConvertTo-Json @($vals)), (New-Object Text.UTF8Encoding $false))
}
function Restore-Original {
  if (Test-Path $backupJs) {
    $vals = [IO.File]::ReadAllText($backupJs) | ConvertFrom-Json
    $k = [Microsoft.Win32.Registry]::CurrentUser.CreateSubKey($cursorKey)
    $saved = @($vals | ForEach-Object { $_.name })
    foreach ($role in $map.Keys) { if ($saved -notcontains $role) { $k.SetValue($role, "") } }
    foreach ($v in $vals) {
      $kind = [Microsoft.Win32.RegistryValueKind]$v.kind
      $val = if ($kind -eq "DWord") { [int]$v.value } else { [string]$v.value }
      $k.SetValue([string]$v.name, $val, $kind)
    }
    $k.Close(); Update-Cursors; return $true
  }
  if (Test-Path $backupReg) {
    $p = Start-Process reg.exe -ArgumentList "import", "`"$backupReg`"" -Wait -PassThru -WindowStyle Hidden
    Update-Cursors; return ($p.ExitCode -eq 0)
  }
  return $false
}

# --- download: Invoke-WebRequest, then curl.exe (built into Windows 10 1803+) ---
function Get-File($urlList, $out) {
  $first = ""
  foreach ($url in @($urlList)) {
    try {
      Invoke-WebRequest $url -OutFile $out -UseBasicParsing -TimeoutSec 120
      return
    } catch { if (-not $first) { $first = $_.Exception.Message } }
    $curl = Join-Path $env:SystemRoot "System32\curl.exe"
    if (Test-Path $curl) {
      $ErrorActionPreference = "Continue"   # PS 5.1 turns native stderr into an error under Stop
      & $curl -fsL --retry 2 --ssl-revoke-best-effort -o $out $url 2>&1 | Out-Null
      if ($LASTEXITCODE -ne 0) { & $curl -fsL --retry 2 -o $out $url 2>&1 | Out-Null }
      $ok = $LASTEXITCODE -eq 0
      $ErrorActionPreference = "Stop"
      if ($ok -and (Test-Path $out)) { return }
    }
  }
  throw "파일을 내려받지 못했습니다. 인터넷 연결이나 보안 프로그램을 확인해 주세요.`n($first)"
}

function Get-ThemeInfo($t, $s) {
  New-Item -ItemType Directory -Force -Path $home2 | Out-Null
  $tmp = "$catalogFile.part"
  try {
    Get-File $catalogUrls $tmp
    Move-Item $tmp $catalogFile -Force
  } catch {
    Remove-Item $tmp -Force -ErrorAction SilentlyContinue
    if (-not (Test-Path $catalogFile)) { throw }
  }
  $cat = [IO.File]::ReadAllText($catalogFile, [Text.Encoding]::UTF8) | ConvertFrom-Json
  $info = $cat.themes | Where-Object { $_.id -eq $t } | Select-Object -First 1
  if (-not $info) { throw "'$t' 커서를 찾지 못했습니다. 페이지를 새로고침한 뒤 다시 눌러 주세요." }
  # packs converted by Clickwee come per size: .../packs/<id>/{size}.zip
  $perSize = @($info.urls | Where-Object { $_ -like "*{size}*" }).Count -gt 0
  $urls = @($info.urls | ForEach-Object { $_.Replace("{size}", $s) } | Where-Object { $_ -match $allowed })
  if (-not $urls.Count) { throw "허용되지 않은 다운로드 주소입니다." }
  $key = "$($info.id)-$($info.rev -replace '[^A-Za-z0-9]', '')"
  if ($perSize) { $key += "-$s" }
  return [pscustomobject]@{ key = $key; urls = $urls; name = $info.name }
}

function Get-Package($info) {
  $pkg = Join-Path $cache $info.key
  if (Test-Path (Join-Path $pkg ".ok")) { return $pkg }
  Notify "커서를 내려받는 중입니다. 잠시만 기다려 주세요."
  New-Item -ItemType Directory -Force -Path $cache | Out-Null
  $tmp = Join-Path $cache ("_" + [guid]::NewGuid().ToString("N"))
  $zip = "$tmp.zip"
  try {
    Get-File $info.urls $zip
    [IO.Compression.ZipFile]::ExtractToDirectory($zip, $tmp)
    Set-Content (Join-Path $tmp ".ok") "ok"
    if (-not (Test-Path (Join-Path $pkg ".ok"))) {   # another click may have finished first
      if (Test-Path $pkg) { Remove-Item $pkg -Recurse -Force }
      Move-Item $tmp $pkg
    }
  } finally {
    Remove-Item $zip -Force -ErrorAction SilentlyContinue
    if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue }
  }
  return $pkg
}

function Apply-Theme($t, $s) {
  if ($t -notmatch '^[A-Za-z0-9_.-]+$') { throw "잘못된 커서 이름입니다: $t" }
  if ($sizes -notcontains $s) { $s = "Regular" }
  $info = Get-ThemeInfo $t $s
  Backup
  $pkg = Get-Package $info
  $src = Get-ChildItem $pkg -Directory | Where-Object {
    $_.Name -like "*-$s-Windows" -and ($s -ne "Large" -or $_.Name -notlike "*Extra-Large*")
  } | Select-Object -First 1
  if (-not $src) { throw "'$t' 에 '$s' 크기가 없습니다." }

  $k = [Microsoft.Win32.Registry]::CurrentUser.CreateSubKey($cursorKey)
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
    $k.SetValue($role, $file, [Microsoft.Win32.RegistryValueKind]::ExpandString)
    $values += $file
  }
  $scheme = "Clickwee $t ($s)"
  $k.SetValue("", $scheme)
  $k.SetValue("Scheme Source", 1, [Microsoft.Win32.RegistryValueKind]::DWord)
  $k.Close()
  $sk = [Microsoft.Win32.Registry]::CurrentUser.CreateSubKey("$cursorKey\Schemes")
  $sk.SetValue($scheme, ($values -join ","), [Microsoft.Win32.RegistryValueKind]::ExpandString)
  $sk.Close()
  Update-Cursors
  # drop older downloads; the current theme's folder stays because the registry points at it
  Get-ChildItem $cache -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -ne $pkg -and $_.Name -notlike "_*" } |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
  return $info.name
}

function Remove-Link {
  Remove-Item $proto -Recurse -Force -ErrorAction SilentlyContinue
  Remove-Item $uninstKey -Recurse -Force -ErrorAction SilentlyContinue
}

try {
  if ($Install) {
    New-Item -ItemType Directory -Force -Path $home2 | Out-Null
    $target = Join-Path $home2 "Clickwee.ps1"
    if ($PSCommandPath -ne $target) { Copy-Item $PSCommandPath $target -Force }
    Backup
    $ps = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
    New-Item -Path $proto -Force | Out-Null
    Set-ItemProperty $proto -Name "(default)" -Value "URL:Clickwee"
    Set-ItemProperty $proto -Name "URL Protocol" -Value ""
    New-Item -Path "$proto\shell\open\command" -Force | Out-Null
    $cmd = "`"$ps`" -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$target`" -Uri `"%1`""
    Set-ItemProperty "$proto\shell\open\command" -Name "(default)" -Value $cmd
    # Also removable from Settings > Apps
    New-Item -Path $uninstKey -Force | Out-Null
    Set-ItemProperty $uninstKey -Name "DisplayName" -Value "Clickwee cursor link"
    Set-ItemProperty $uninstKey -Name "Publisher" -Value "Clickwee"
    Set-ItemProperty $uninstKey -Name "DisplayVersion" -Value "$Version"
    Set-ItemProperty $uninstKey -Name "NoModify" -Value 1 -Type DWord
    Set-ItemProperty $uninstKey -Name "NoRepair" -Value 1 -Type DWord
    Set-ItemProperty $uninstKey -Name "UninstallString" -Value "`"$ps`" -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$target`" -Uri clickwee://uninstall"
    Write-Host "  Connected. Go back to the website and click Apply." -ForegroundColor Green
    return
  }
  if ($Uninstall) {
    Restore-Original | Out-Null
    Remove-Link
    Write-Host "  Removed. Original cursors restored." -ForegroundColor Green
    return
  }
  if ($Uri) {
    $parts = @((($Uri -replace '^clickwee:/*', '') -replace '[?#].*$', '').Trim('/') -split '/')
    switch ($parts[0]) {
      "uninstall" {
        Restore-Original | Out-Null
        Remove-Link
        Remove-Item $cache -Recurse -Force -ErrorAction SilentlyContinue
        Say "Clickwee 연결을 해제하고 원래 커서로 되돌렸습니다."
        return
      }
      "restore" {
        if (Restore-Original) { Notify "원래 커서로 되돌렸습니다." }
        else { Say "백업이 없습니다. 설정 > 마우스 > 추가 마우스 설정 > 포인터에서 'Windows 기본값'을 고르세요." "Warning" }
        Close-Tray
        return
      }
      "apply" {
        if ($parts.Count -lt 2) { break }
        $s = "Regular"; if ($parts.Count -ge 3) { $s = $parts[2] }
        $name = Apply-Theme $parts[1] $s
        Notify "$name 커서를 적용했습니다."
        Close-Tray
        return
      }
    }
    throw "잘못된 링크입니다: $Uri"
  }
  if ($Restore) { Restore-Original | Out-Null; return }
  if ($Theme) { Apply-Theme $Theme $Size | Out-Null; Write-Host "Done." -ForegroundColor Green; return }
} catch {
  if ($script:tray) { $script:tray.Dispose() }
  if ($Uri) { Say ("커서를 적용하지 못했습니다.`n`n" + $_.Exception.Message) "Error" } else { throw }
}
