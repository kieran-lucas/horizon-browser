param(
  [string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

$chromiumRoot = Join-Path $RepositoryRoot '.engine\chromium\src'
$sourcePath = Join-Path $chromiumRoot 'chrome\browser\resources\new_tab_page\icons\horizon_mark.png'
& (Join-Path $PSScriptRoot 'create-ntp-mark.ps1') -RepositoryRoot $RepositoryRoot
$source = [System.Drawing.Image]::FromFile($sourcePath)

function Write-ScaledPng([string]$Path, [int]$Size) {
  $bitmap = [System.Drawing.Bitmap]::new($Size, $Size, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
  $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
  try {
    $graphics.Clear([System.Drawing.Color]::Transparent)
    $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
    $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
    $graphics.DrawImage($source, [System.Drawing.Rectangle]::new(0, 0, $Size, $Size),
      [System.Drawing.Rectangle]::new(0, 0, $source.Width, $source.Height),
      [System.Drawing.GraphicsUnit]::Pixel)
    $bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
  } finally {
    $graphics.Dispose()
    $bitmap.Dispose()
  }
}

try {
  $theme = Join-Path $chromiumRoot 'chrome\app\theme'
  $iconSizes = @(16, 24, 32, 48, 64, 128, 256)
  $temporaryPngs = @{}
  foreach ($size in $iconSizes) {
    $temporaryPngs[$size] = Join-Path $env:TEMP "horizon-app-icon-$size.png"
    Write-ScaledPng $temporaryPngs[$size] $size
  }

  foreach ($size in @(16, 24, 48, 64, 128, 256)) {
    Copy-Item -LiteralPath $temporaryPngs[$size] -Destination (Join-Path $theme "chromium\product_logo_$size.png") -Force
  }
  foreach ($size in @(16, 32)) {
    Copy-Item -LiteralPath $temporaryPngs[$size] -Destination (Join-Path $theme "default_100_percent\chromium\product_logo_$size.png") -Force
    Copy-Item -LiteralPath $temporaryPngs[($size * 2)] -Destination (Join-Path $theme "default_200_percent\chromium\product_logo_$size.png") -Force
  }
  Copy-Item -LiteralPath $temporaryPngs[16] -Destination (Join-Path $theme 'default_100_percent\common\favicon_ntp.png') -Force
  Copy-Item -LiteralPath $temporaryPngs[32] -Destination (Join-Path $theme 'default_200_percent\common\favicon_ntp.png') -Force
  foreach ($tileName in @('SmallLogo.png', 'Logo.png')) {
    $tilePath = Join-Path $theme "chromium\win\tiles\$tileName"
    $tile = [System.Drawing.Image]::FromFile($tilePath)
    $size = $tile.Width
    $tile.Dispose()
    Write-ScaledPng $tilePath $size
  }

  $icoPath = Join-Path $theme 'chromium\win\chromium.ico'
  $stream = [System.IO.File]::Create($icoPath)
  $writer = [System.IO.BinaryWriter]::new($stream)
  try {
    $writer.Write([uint16]0)
    $writer.Write([uint16]1)
    $writer.Write([uint16]$iconSizes.Count)
    $offset = 6 + 16 * $iconSizes.Count
    foreach ($size in $iconSizes) {
      $bytes = [System.IO.File]::ReadAllBytes($temporaryPngs[$size])
      $writer.Write([byte]($size % 256))
      $writer.Write([byte]($size % 256))
      $writer.Write([byte]0)
      $writer.Write([byte]0)
      $writer.Write([uint16]1)
      $writer.Write([uint16]32)
      $writer.Write([uint32]$bytes.Length)
      $writer.Write([uint32]$offset)
      $offset += $bytes.Length
    }
    foreach ($size in $iconSizes) {
      $writer.Write([System.IO.File]::ReadAllBytes($temporaryPngs[$size]))
    }
  } finally {
    $writer.Dispose()
  }
} finally {
  $source.Dispose()
}
