"""Build Clickwee-Connect.bat with Clickwee.ps1 embedded in it.

The .bat no longer downloads anything from clickwee.com, so it works even when the
site's HTTPS certificate is broken. Run after editing Clickwee.ps1:
    python3 tools/build_connect.py
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARKER = "#CLICKWEE-PS1-BELOW#"

# Batch part must stay ASCII: cmd.exe reads it in the console code page.
BAT = r"""@echo off
setlocal
title Clickwee
echo.
echo   Clickwee - connecting this PC ...
echo.
set "CW_SELF=%~f0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $d=Join-Path $env:LOCALAPPDATA 'Clickwee'; New-Item -ItemType Directory -Force -Path $d | Out-Null; $t=[IO.File]::ReadAllText($env:CW_SELF,[Text.Encoding]::UTF8); $i=$t.LastIndexOf('%MARKER%'); if($i -lt 0){throw 'broken file'}; $p=Join-Path $d 'Clickwee.ps1'; [IO.File]::WriteAllText($p,$t.Substring($t.IndexOf([char]10,$i)+1),(New-Object Text.UTF8Encoding $true)); & $p -Install"
if errorlevel 1 (
  echo.
  echo   Setup failed. Please send a screenshot of this window to clickwee.com.
  echo.
  pause
  exit /b 1
)
echo.
echo   Done. Go back to clickwee.com and pick a cursor.
echo   This window closes in 5 seconds.
timeout /t 5 >nul
exit /b 0
""".replace("%MARKER%", MARKER)


def main():
    ps1 = (ROOT / "Clickwee.ps1").read_text(encoding="utf-8-sig")
    assert MARKER not in ps1
    out = BAT + MARKER + "\n" + ps1
    out = out.replace("\r\n", "\n").replace("\n", "\r\n")
    (ROOT / "Clickwee-Connect.bat").write_bytes(out.encode("utf-8"))  # no BOM: cmd.exe would choke


if __name__ == "__main__":
    main()
