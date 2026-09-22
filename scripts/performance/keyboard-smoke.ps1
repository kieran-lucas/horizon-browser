param()

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$exe = Join-Path $root '.engine/chromium/src/out/phase0/chrome.exe'
$artifactRoot = (Resolve-Path (Join-Path $root 'performance-artifacts')).Path
$profile = Join-Path $artifactRoot 'keyboard-profile'
if ([IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($profile)) -ne [IO.Path]::GetFullPath($artifactRoot)) {
  throw 'Unexpected profile path'
}
if (Test-Path -LiteralPath $profile) {
  Remove-Item -LiteralPath $profile -Recurse -Force
}

Add-Type -AssemblyName System.Windows.Forms
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class HorizonKeyboardNative {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hwnd);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hwnd, out uint pid);
  [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint flags, UIntPtr extra);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
}
'@

$process = Start-Process -FilePath $exe -ArgumentList @(
  "--user-data-dir=$profile", '--no-first-run', '--no-default-browser-check', 'chrome://newtab/'
) -WindowStyle Normal -PassThru
try {
  $window = [IntPtr]::Zero
  for ($i = 0; $i -lt 120; $i++) {
    Start-Sleep -Milliseconds 250
    $process.Refresh()
    $window = $process.MainWindowHandle
    if ($window -ne [IntPtr]::Zero) { break }
  }
  if ($window -eq [IntPtr]::Zero) {
    Write-Output 'foreground_unavailable: no Horizon window appeared'
    return
  }
  # Windows foreground activation can require an input event from this process.
  [HorizonKeyboardNative]::keybd_event(0x12, 0, 0, [UIntPtr]::Zero)
  [HorizonKeyboardNative]::keybd_event(0x12, 0, 2, [UIntPtr]::Zero)
  [HorizonKeyboardNative]::SetForegroundWindow($window) | Out-Null
  Start-Sleep -Milliseconds 250
  [uint32]$foregroundPid = 0
  [HorizonKeyboardNative]::GetWindowThreadProcessId(
    [HorizonKeyboardNative]::GetForegroundWindow(), [ref]$foregroundPid) | Out-Null
  if ($foregroundPid -ne $process.Id) {
    Write-Output "foreground_unavailable: active PID $foregroundPid, Horizon PID $($process.Id)"
    return
  }

  Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
  $automationRoot = [System.Windows.Automation.AutomationElement]::FromHandle($window)
  $allControls = $automationRoot.FindAll(
    [System.Windows.Automation.TreeScope]::Descendants,
    [System.Windows.Automation.Condition]::TrueCondition)
  $toolbarControls = @()
  $hoverTargets = @()
  foreach ($control in $allControls) {
    $bounds = $control.Current.BoundingRectangle
    if (!$bounds.IsEmpty -and $bounds.Top -lt 200 -and
        $bounds.Width -lt 600 -and $control.Current.Name) {
      $toolbarControls += $control.Current.Name
      if ($control.Current.Name -in @('Back', 'Forward', 'Reload')) {
        $hoverTargets += [pscustomobject]@{
          name = $control.Current.Name
          x = [int]($bounds.X + $bounds.Width / 2)
          y = [int]($bounds.Y + $bounds.Height / 2)
        }
      }
    }
  }
  Write-Output "toolbar_controls=$($toolbarControls -join ', ')"

  [System.Windows.Forms.SendKeys]::SendWait('^l')
  [System.Windows.Forms.SendKeys]::SendWait('chrome://settings/')
  [System.Windows.Forms.SendKeys]::SendWait('{ENTER}')
  Start-Sleep -Milliseconds 1000
  $process.Refresh()
  $settingsTitle = $process.MainWindowTitle
  for ($i = 0; $i -lt 10; $i++) {
    [System.Windows.Forms.SendKeys]::SendWait('^t')
  }
  for ($i = 0; $i -lt 30; $i++) {
    [System.Windows.Forms.SendKeys]::SendWait('^{TAB}')
  }
  for ($i = 0; $i -lt 10; $i++) {
    [System.Windows.Forms.SendKeys]::SendWait('^w')
  }
  $tabBounds = $automationRoot.Current.BoundingRectangle
  for ($i = 0; $i -lt 20; $i++) {
    foreach ($offset in @(260, 360, 460, 560, 660)) {
      [HorizonKeyboardNative]::SetCursorPos(
        [int]($tabBounds.X + $offset), [int]($tabBounds.Y + 24)) | Out-Null
      Start-Sleep -Milliseconds 15
    }
  }
  for ($i = 0; $i -lt 20; $i++) {
    foreach ($target in $hoverTargets) {
      [HorizonKeyboardNative]::SetCursorPos($target.x, $target.y) | Out-Null
      Start-Sleep -Milliseconds 15
    }
  }
  $windowBounds = $automationRoot.Current.BoundingRectangle
  [HorizonKeyboardNative]::SetCursorPos(
    [int]($windowBounds.X + $windowBounds.Width / 2),
    [int]($windowBounds.Y + $windowBounds.Height / 2)) | Out-Null
  for ($i = 0; $i -lt 10; $i++) {
    [System.Windows.Forms.SendKeys]::SendWait('%f')
    Start-Sleep -Milliseconds 30
    [System.Windows.Forms.SendKeys]::SendWait('{ESC}')
  }
  [System.Windows.Forms.SendKeys]::SendWait('^+m')
  Start-Sleep -Milliseconds 150
  [System.Windows.Forms.SendKeys]::SendWait('{ESC}')
  Start-Sleep -Milliseconds 300
  $process.Refresh()
  Write-Output "settings_title=$settingsTitle"
  Write-Output "after_rapid_shortcuts_title=$($process.MainWindowTitle)"
  Write-Output "hover_targets=$($hoverTargets.name -join ', ')"
  Write-Output 'tab_strip_hover=20 sweeps across five positions'
  Write-Output 'sent=Ctrl+L, URL, 10x Ctrl+T, 30x Ctrl+Tab, 10x Ctrl+W, 20x toolbar hover, 10x menu, profile popup'
} finally {
  if (-not $process.HasExited) {
    taskkill /PID $process.Id /T /F | Out-Null
  }
}
