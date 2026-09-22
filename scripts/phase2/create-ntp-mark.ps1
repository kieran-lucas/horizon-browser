param(
  [string]$RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$drawingAssemblies = [AppDomain]::CurrentDomain.GetAssemblies() |
  Where-Object { $_.GetName().Name -match '^(System\.Drawing|System\.Private\.Windows\.)' } |
  Select-Object -ExpandProperty Location
Add-Type -ReferencedAssemblies $drawingAssemblies -TypeDefinition @'
using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;

public static class HorizonNtpMark {
  public static void Create(string inputPath, string outputPath) {
    using (var source = Image.FromFile(inputPath))
    using (var image = new Bitmap(source.Width, source.Height, PixelFormat.Format32bppArgb)) {
      using (var graphics = Graphics.FromImage(image)) {
        graphics.DrawImage(source, 0, 0, source.Width, source.Height);
      }

      var rect = new Rectangle(0, 0, image.Width, image.Height);
      var data = image.LockBits(rect, ImageLockMode.ReadWrite, PixelFormat.Format32bppArgb);
      int left = image.Width, top = image.Height, right = 0, bottom = 0;
      try {
        var pixels = new byte[data.Stride * data.Height];
        Marshal.Copy(data.Scan0, pixels, 0, pixels.Length);
        for (int y = 0; y < image.Height; ++y) {
          for (int x = 0; x < image.Width; ++x) {
            int offset = y * data.Stride + x * 4;
            int blue = pixels[offset];
            int red = pixels[offset + 2];
            int alpha = Math.Max(0, Math.Min(255, (blue - red - 35) * 255 / 45));
            // The supplied square artwork also has a pale rounded card and
            // shadow. Keep only its central horizon silhouette.
            if (x < 180 || x > 1070 || y < 240 || y > 1000)
              alpha = 0;
            pixels[offset + 3] = (byte)alpha;
            if (alpha > 12) {
              left = Math.Min(left, x);
              top = Math.Min(top, y);
              right = Math.Max(right, x);
              bottom = Math.Max(bottom, y);
            }
          }
        }
        Marshal.Copy(pixels, 0, data.Scan0, pixels.Length);
      } finally {
        image.UnlockBits(data);
      }

      var crop = Rectangle.FromLTRB(left, top, right + 1, bottom + 1);
      using (var output = new Bitmap(256, 256, PixelFormat.Format32bppArgb))
      using (var graphics = Graphics.FromImage(output)) {
        graphics.Clear(Color.Transparent);
        graphics.InterpolationMode = InterpolationMode.HighQualityBicubic;
        graphics.SmoothingMode = SmoothingMode.HighQuality;
        graphics.PixelOffsetMode = PixelOffsetMode.HighQuality;
        float scale = 240f / Math.Max(crop.Width, crop.Height);
        float width = crop.Width * scale, height = crop.Height * scale;
        graphics.DrawImage(image,
            new RectangleF((256f - width) / 2, (256f - height) / 2, width, height),
            crop, GraphicsUnit.Pixel);
        output.Save(outputPath, ImageFormat.Png);
      }
    }
  }
}
'@

$source = Join-Path $RepositoryRoot 'app_icon.png'
$output = Join-Path $RepositoryRoot '.engine\chromium\src\chrome\browser\resources\new_tab_page\icons\horizon_mark.png'
[HorizonNtpMark]::Create($source, $output)
