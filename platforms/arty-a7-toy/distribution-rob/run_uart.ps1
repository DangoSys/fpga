# 临时配置 ROB/PR10 位流，读回完整软件镜像并执行 Linux/Gemmini 回归。
param(
    [Parameter(Mandatory = $true)][string]$Port,
    [Parameter(Mandatory = $true)][string]$Vivado,
    [string]$Python = 'python'
)
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
Push-Location -LiteralPath $PSScriptRoot
try {
    & $Python verify_bundle.py
    if ($LASTEXITCODE -ne 0) { throw '下载包校验失败，取消烧录' }
    $releaseManifest = Get-Content -LiteralPath MANIFEST.json -Raw -Encoding UTF8 | ConvertFrom-Json
    $bitDigest = $releaseManifest.files.'toy_a7_uart.bit'.sha256
    & $Python host/check_linux_gemmini.py --payload fw_payload.bin `
        --build-result LINUX_GEMMINI_BUILD.json --bitstream toy_a7_uart.bit `
        --expected-bit-sha256 $bitDigest --vivado $Vivado --port $Port
    if ($LASTEXITCODE -ne 0) { throw '加载或测试失败，请查看 build/ 中的记录' }
} finally {
    Pop-Location
}
