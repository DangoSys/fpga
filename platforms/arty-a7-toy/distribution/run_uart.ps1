# 临时配置 FPGA、完整 DDR 读回、Linux/Gemmini 回归；不写 Flash。
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
    & $Python host/check_linux_gemmini.py --payload fw_payload.bin `
        --build-result LINUX_GEMMINI_BUILD.json --bitstream toy_a7_uart.bit `
        --vivado $Vivado --port $Port
    if ($LASTEXITCODE -ne 0) { throw '临时加载或测试失败，请查看 build/ 中的记录' }
} finally {
    Pop-Location
}
