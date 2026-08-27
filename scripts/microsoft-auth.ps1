# Optional Windows helper — print/copy the current MFA code.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Script = Join-Path $Root "scripts\microsoft-auth.py"

$PythonCmd = $null
foreach ($name in @("python", "py")) {
  $found = Get-Command $name -ErrorAction SilentlyContinue
  if ($found) {
    $PythonCmd = $found.Source
    break
  }
}

if (-not $PythonCmd) {
  Write-Error "Python was not found on PATH."
  exit 1
}

& $PythonCmd $Script @args
exit $LASTEXITCODE
