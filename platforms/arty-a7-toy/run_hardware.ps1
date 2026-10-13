# Prepare the pinned UART release and reuse the Linux/Gemmini verifier.
param(
    [string]$Port,
    [string]$Vivado,
    [string]$Python = 'python',
    [string]$BundleZip,
    [switch]$PrepareOnly
)
$ErrorActionPreference = 'Stop'
$entry = Join-Path $PSScriptRoot 'scripts/run_hardware.py'
$entryArgs = @('-X', 'utf8', $entry)
if ($PrepareOnly) { $entryArgs += '--prepare-only' }
if ($Port) { $entryArgs += @('--port', $Port) }
if ($Vivado) { $entryArgs += @('--vivado', $Vivado) }
if ($BundleZip) { $entryArgs += @('--bundle-zip', $BundleZip) }
& $Python @entryArgs
if ($LASTEXITCODE -ne 0) { throw "Hardware verification failed (exit code $LASTEXITCODE); see the error and RUN.json above." }
