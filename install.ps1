# Thin wrapper around the cross-platform Python installer (Windows).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$InstallPy = Join-Path $Root "install.py"

$PythonCmd = $null
foreach ($name in @("python", "py")) {
  $found = Get-Command $name -ErrorAction SilentlyContinue
  if ($found) {
    $PythonCmd = $found.Source
    break
  }
}

if (-not $PythonCmd) {
  Write-Error "Python was not found. Install Python 3 from https://www.python.org/downloads/ (enable Add to PATH) and re-run."
  exit 1
}

& $PythonCmd $InstallPy @args
exit $LASTEXITCODE
