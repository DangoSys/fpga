param(
  [string]$VivadoBin = $env:VIVADO_BIN,
  [Parameter(Mandatory = $true)][string]$Bitstream
)
$ErrorActionPreference = "Stop"
if (!$VivadoBin) { $VivadoBin = Split-Path (Get-Command vivado.bat -ErrorAction Stop).Source }
if (!(Test-Path -LiteralPath $Bitstream -PathType Leaf)) { throw "Bitstream not found: $Bitstream" }
$toyBitstreamPath = (Resolve-Path -LiteralPath $Bitstream).ProviderPath
Push-Location $PSScriptRoot
try {
  & (Join-Path $VivadoBin "vivado.bat") -mode batch -source (Join-Path $PSScriptRoot "program.tcl") -tclargs $toyBitstreamPath
  if ($LASTEXITCODE -ne 0) { throw "FPGA programming failed; inspect Vivado log" }
} finally { Pop-Location }
