param(
  [string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
)

$ErrorActionPreference = 'Stop'
$back = 'M2.6 10 C2.6 9.55 2.85 9.22 3.3 8.88 L9.5 4.1 C10.15 3.65 10.95 4.07 10.95 4.9 L10.95 7.9 C13.2 7.85 16 8.42 17.55 9.28 C18.15 9.62 18.15 10.38 17.55 10.72 C16 11.58 13.2 12.15 10.95 12.1 L10.95 15.1 C10.95 15.93 10.15 16.35 9.5 15.9 L3.3 11.12 C2.85 10.78 2.6 10.45 2.6 10 Z'
$forward = 'M17.4 10 C17.4 9.55 17.15 9.22 16.7 8.88 L10.5 4.1 C9.85 3.65 9.05 4.07 9.05 4.9 L9.05 7.9 C6.8 7.85 4 8.42 2.45 9.28 C1.85 9.62 1.85 10.38 2.45 10.72 C4 11.58 6.8 12.15 9.05 12.1 L9.05 15.1 C9.05 15.93 9.85 16.35 10.5 15.9 L16.7 11.12 C17.15 10.78 17.4 10.45 17.4 10 Z'
$reload = 'M12.15 14.15 C9.95 17.35 5.75 16.9 3.7 13.55 C1.15 9.45 3.55 4.8 7.35 3.15 C10.45 1.8 13.2 2.75 15 4.2 L15.38 2.4 C15.51 1.78 16.26 1.68 16.68 2.25 L19.13 5.92 C19.59 6.61 19.36 7.3 18.61 7.57 L13.66 9.13 C12.87 9.38 12.29 8.62 12.75 7.96 L13.83 6.46 C11.92 5.08 9.93 4.99 8.23 5.81 C5.5 7.12 4.65 10.3 6.21 12.76 C7.52 14.83 10.07 15.52 12.15 14.15 Z'
$stop = 'M7.2 5.1 L12.8 5.1 C14 5.1 14.9 6 14.9 7.2 L14.9 12.8 C14.9 14 14 14.9 12.8 14.9 L7.2 14.9 C6 14.9 5.1 14 5.1 12.8 L5.1 7.2 C5.1 6 6 5.1 7.2 5.1 Z'

$paths = @{}
foreach ($name in @('arrow_back', 'back_arrow_chrome_refresh_old', 'back_arrow_touch_old')) { $paths[$name] = $back }
foreach ($name in @('arrow_forward', 'forward_arrow_chrome_refresh_old', 'forward_arrow_touch_old')) { $paths[$name] = $forward }
foreach ($name in @('refresh', 'reload_chrome_refresh_old', 'reload_touch_old')) { $paths[$name] = $reload }
foreach ($name in @('navigate_stop_chrome_refresh_old', 'navigate_stop_touch_old')) { $paths[$name] = $stop }

$file = Join-Path $RepositoryRoot '.engine\chromium\src\chrome\browser\resources\webui_toolbar\icons.ts'
$lines = [System.IO.File]::ReadAllLines($file)
$updated = @{}
for ($index = 0; $index -lt $lines.Length; $index++) {
  if ($lines[$index] -notmatch "^\s*'([^']+)':") { continue }
  $name = $Matches[1]
  if (!$paths.ContainsKey($name)) { continue }
  for ($target = $index; $target -le [Math]::Min($index + 2, $lines.Length - 1); $target++) {
    if (!$lines[$target].Contains("id=`"$name`"")) { continue }
    $lines[$target] = [regex]::Replace($lines[$target], 'viewBox="[^"]+"', 'viewBox="0 0 20 20"', 1)
    $lines[$target] = [regex]::Replace($lines[$target], '<path d="[^"]+"', '<path d="' + $paths[$name] + '"', 1)
    $updated[$name] = $true
    break
  }
}
if ($updated.Count -ne $paths.Count) { throw "Updated $($updated.Count) of $($paths.Count) toolbar icons" }
$utf8 = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText($file, ([string]::Join("`n", $lines) + "`n"), $utf8)
