param(
    [Parameter(Mandatory=$true)][ValidatePattern('^[A-Za-z0-9_-]+$')][string]$Serial,
    [Parameter(Mandatory=$true)][string]$Image,
    [Parameter(Mandatory=$true)][string]$Manifest,
    [Parameter(Mandatory=$true)][string]$Fastboot,
    [Parameter(Mandatory=$true)][string]$Python,
    [Parameter(Mandatory=$true)][string]$LogPath
)
$ErrorActionPreference = 'Stop'
$imagePath = (Resolve-Path -LiteralPath $Image).Path
$manifestPath = (Resolve-Path -LiteralPath $Manifest).Path
& $Python (Join-Path $PSScriptRoot 'verify-boot.py') $imagePath $manifestPath
if ($LASTEXITCODE -ne 0) { throw 'Boot verification failed; nothing flashed' }
$record = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$actualHash = (Get-FileHash -LiteralPath $imagePath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualHash -ne $record.sha256) { throw 'Image changed after verification' }
$devices = @(& $Fastboot devices)
if ($LASTEXITCODE -ne 0) { throw 'Cannot enumerate fastboot' }
$phoneMatches = @($devices | Where-Object { ($_ -split '\s+')[0] -ceq $Serial -and ($_ -split '\s+')[1] -eq 'fastboot' })
if ($phoneMatches.Count -ne 1) { throw 'Requested phone is not present exactly once; nothing flashed' }
# PowerShell 5.1 promotes native stderr lines to terminating errors while EAP=Stop and
# output is redirected; fastboot always emits a benign avb-footer warning to stderr.
# Every failure path below uses explicit throw, so relaxing EAP here is safe.
$ErrorActionPreference = 'Continue'
$start = Get-Date -Format o
Add-Content -LiteralPath $LogPath -Value "$start serial=$Serial image_sha256=$actualHash action=flash_boot_only"
$flashOutput = @(& $Fastboot -s $Serial flash boot $imagePath 2>&1)
$flashCode = $LASTEXITCODE
$flashOutput | Add-Content -LiteralPath $LogPath
$flashOutput | Write-Output
if ($flashCode -ne 0) { throw "fastboot flash boot failed: $flashCode" }
# This helper never erases another partition and never auto-reboots on a failed write.
& $Fastboot -s $Serial reboot
if ($LASTEXITCODE -ne 0) { throw 'Boot written, but reboot failed; inspect fastboot state' }
Add-Content -LiteralPath $LogPath -Value "$(Get-Date -Format o) flash_boot_success reboot_requested"
