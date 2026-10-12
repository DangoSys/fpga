# 固化配套 MCS：先备份 Flash，再擦写/校验，最后核验自主启动。
param(
    [Parameter(Mandatory = $true)][string]$Port,
    [Parameter(Mandatory = $true)][string]$Vivado,
    [Parameter(Mandatory = $true)]
    [ValidateSet('s25fl128sxxxxxx0-spi-x1_x2_x4',
                 's25fl128sxxxxxx1-spi-x1_x2_x4',
                 'mt25ql128-spi-x1_x2_x4')][string]$FlashPart,
    [string]$Python = 'python'
)
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
Push-Location -LiteralPath $PSScriptRoot
try {
    & $Python verify_bundle.py
    if ($LASTEXITCODE -ne 0) { throw '下载包校验失败，取消烧录' }
    & $Python host/flash.py --bitstream toy_a7_flash.bit `
        --payload flash_payload.bin --mcs toy_flash.mcs --part $FlashPart `
        --vivado $Vivado --port $Port
    if ($LASTEXITCODE -ne 0) { throw 'Flash 烧写或启动检查失败，请查看 build/ 中的记录' }
} finally {
    Pop-Location
}
